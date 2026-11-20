"""Dataset adapters -> one manifest.csv (path,label,source,generator,split). label: 1 = AI-generated, 0 = real.

CIFAKE's layout is well known. ArtiFact / GenImage / Synthbuster adapters were written from their public
documentation and verify what they find at run time (they print counts and stop with a clear message if
the folder layout is not what is expected) - because I could not download them while writing this.
"""
from __future__ import annotations

import hashlib
import random
import time
import zipfile
from pathlib import Path

import pandas as pd

from app.attribution import family_of

from .common import Ctx, log

EXT = {".jpg", ".jpeg", ".png", ".webp"}

DATASETS_INFO = [
    {"name": "CIFAKE", "role": "training (baseline) + test", "url": "https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images"},
    {"name": "ArtiFact", "role": "training + test (25 generators)", "url": "https://github.com/awsaf49/artifact"},
    {"name": "GenImage", "role": "training + test (subset)", "url": "https://github.com/GenImage-Dataset/GenImage"},
    {"name": "OpenFake", "role": "training + test (generator-labelled, generator attribution)", "url": "https://huggingface.co/datasets/ComplexDataLab/OpenFake"},
    {"name": "Generator folders", "role": "your own generator-labelled images", "url": "local folder (--generator-root)"},
    {"name": "Synthbuster", "role": "unseen-generator test only", "url": "https://zenodo.org/records/10066460"},
    {"name": "RAISE", "role": "real camera photos for the unseen-generator test", "url": "http://loki.disi.unitn.it/RAISE/"},
]


def _images(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXT)


def _take(items: list, n: int, rng: random.Random) -> list:
    items = list(items)
    rng.shuffle(items)
    return items[:n] if n else items


def _rows(paths, label, source, generator, split) -> list[dict]:
    fam = family_of(generator) if label == 1 else None
    # attr_ok=False for CIFAKE: every image is 32x32, which would teach the attribution head "tiny image = Stable Diffusion"
    return [{"path": str(p), "label": label, "source": source, "generator": generator, "split": split,
             "family": fam, "attr_ok": source != "CIFAKE"} for p in paths]


def _split_random(rows: list[dict], rng: random.Random, val=0.1, test=0.1) -> None:
    """Stratified train/val/test split: every (label, generator) group is split 80/10/10 on its own, so each split has
    the same real/AI ratio and the same generator mix (a plain shuffle can leave a small generator out of val/test)."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["label"], r["generator"]), []).append(r)
    for key in sorted(groups, key=str):              # sorted -> reproducible with the same seed
        g = groups[key]
        rng.shuffle(g)
        n_test, n_val = round(len(g) * test), round(len(g) * val)
        for i, r in enumerate(g):
            r["split"] = "test" if i < n_test else "val" if i < n_test + n_val else "train"


def dedup_and_check_leakage(df: pd.DataFrame, report_path) -> pd.DataFrame:
    """Data-leakage guard: the SAME image (byte-identical, SHA-256) must never sit in two splits.

    * duplicate across splits  -> kept in the 'strongest' split only (train > val > test), removed elsewhere
    * duplicate inside a split -> kept once
    * same bytes labelled both real and fake -> dropped entirely (label noise)
    * missing, empty or unreadable (corrupt) image files -> dropped and counted, so no stage trains on holes
    Near-duplicates (resized/re-encoded copies) are NOT detected; this limitation is documented in the model card.
    """
    import json
    from concurrent.futures import ThreadPoolExecutor

    import io

    from PIL import Image

    def h(path: str) -> str | None:
        try:
            with open(path, "rb") as f:
                data = f.read()
            with Image.open(io.BytesIO(data)) as im:
                im.verify()                         # header + structure check without decoding all pixels
            return hashlib.sha256(data).hexdigest()
        except Exception:  # noqa: BLE001 - missing / truncated / not an image
            return None

    with ThreadPoolExecutor(8) as ex:
        df = df.assign(sha=list(ex.map(h, df["path"])))
    bad = df["sha"].isna()
    n_bad = int(bad.sum())
    if n_bad:
        log.warning("leakage check: %d missing or unreadable image files dropped (per source: %s)",
                    n_bad, df[bad].groupby("source").size().to_dict())
    df = df[~bad]
    before = len(df) + n_bad
    conflict = df.groupby("sha")["label"].nunique()
    conflict_hashes = set(conflict[conflict > 1].index)
    df = df[~df["sha"].isin(conflict_hashes)]
    rank = {"train": 0, "val": 1, "test": 2}
    df = df.assign(_r=df["split"].map(rank)).sort_values("_r", kind="stable")
    cross = df.groupby("sha")["split"].nunique()
    n_cross = int((cross > 1).sum())
    df = df.drop_duplicates("sha", keep="first").drop(columns="_r")
    rep = {"images_before": before, "unreadable_removed": n_bad, "label_conflicts_removed": len(conflict_hashes), "hashes_in_multiple_splits": n_cross,
           "images_after": len(df), "removed_total": before - len(df)}
    report_path.write_text(json.dumps(rep, indent=2))
    log.info("leakage check: %s", rep)
    return df.drop(columns="sha")


def _stratified_sample(g: pd.DataFrame, k: int, seed: int) -> pd.DataFrame:
    """k rows of g, keeping each generator's share (largest-remainder allocation) instead of a plain random sample."""
    if k >= len(g):
        return g
    gen = g["generator"].astype(str)
    counts = gen.value_counts().sort_index()
    exact = counts / counts.sum() * k
    alloc = exact.astype(int)
    for name in (exact - alloc).sort_values(ascending=False, kind="stable").index[: k - int(alloc.sum())]:
        alloc[name] += 1
    return pd.concat([g[gen == name].sample(n=int(n), random_state=seed) for name, n in alloc.items() if n])


def balance(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Equal numbers of REAL and AI images within every (source, split) - so every split is 50/50 real/AI overall and
    the model cannot use the source as a clue. The larger class is cut down stratified by generator."""
    parts = []
    for _, g in df.groupby(["source", "split"]):
        n = g["label"].value_counts()
        k = int(n.min()) if len(n) == 2 else 0     # a (source, split) with only one class is dropped
        if not k:
            continue
        for _, gl in g.groupby("label"):
            parts.append(_stratified_sample(gl, k, seed))
    return pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0]


REQUIRED_SOURCES = ("CIFAKE",)          # the pipeline cannot work without these -> never shrunk by the cap


def _family_floor(split: str, attr_min: int) -> int:
    """Fewest AI images a generator family keeps per split under the cap, so stage 6b can still train on it
    (it needs attr_min TRAIN images per family; val/test need a few for temperature scaling / the report)."""
    return attr_min + max(2, attr_min // 4) if split == "train" else max(2, attr_min // 6)


def _cap_ai(g: pd.DataFrame, k: int, floor: int, seed: int) -> pd.DataFrame:
    """k AI rows, proportional per family but never below `floor` for a family (if it had that many), then
    stratified by generator inside each family."""
    fam = g["family"].fillna("-").astype(str)
    counts = fam.value_counts().sort_index()
    keep = {f: min(int(c), floor) for f, c in counts.items()}          # floors first
    rest = max(0, k - sum(keep.values()))
    extra = {f: int(c) - keep[f] for f, c in counts.items()}
    tot = sum(extra.values())
    if tot and rest:
        share = {f: extra[f] * min(1.0, rest / tot) for f in extra}
        for f in share:
            keep[f] += int(share[f])
    return pd.concat([_stratified_sample(g[fam == f], n, seed) for f, n in keep.items() if n])


def cap_total(df: pd.DataFrame, max_images: int, seed: int, attr_min: int = 0) -> pd.DataFrame:
    """Shrink a balanced manifest to about max_images.

    * REQUIRED_SOURCES (CIFAKE) are kept complete; only the other datasets are shrunk to fill the remaining budget.
    * Every (source, split) is shrunk by the same fraction, AI side per generator family with a floor (attribution
      keeps >= attr_min training images per family), real side to exactly the same count -> real = AI everywhere.
    * The 80/10/10 split and the generator mix inside each group are kept; no source loses its val/test images.
    The floors can push the total slightly over max_images; that is logged."""
    if not max_images or len(df) <= max_images:
        return df
    req = df[df["source"].isin(REQUIRED_SOURCES)]
    opt = df[~df["source"].isin(REQUIRED_SOURCES)]
    if opt.empty:
        log.warning("dataset cap: only required datasets present (%d images) - nothing to shrink", len(df))
        return df
    budget = max_images - len(req)
    f = max(0.0, min(1.0, budget / len(opt)))
    parts = [req]
    for (_, split), g in opt.groupby(["source", "split"]):
        ai, real = g[g.label == 1], g[g.label == 0]
        k = max(1, int(len(ai) * f))
        ai_kept = _cap_ai(ai, k, _family_floor(split, attr_min) if attr_min else 1, seed)
        parts += [ai_kept, _stratified_sample(real, min(len(real), len(ai_kept)), seed)]
    out = pd.concat(parts, ignore_index=True)
    log.info("dataset cap: %d -> %d images (max_images=%d; required %s kept complete: %d; others shrunk to ~%.1f %%)",
             len(df), len(out), max_images, "/".join(REQUIRED_SOURCES), len(req), f * 100)
    if len(out) > max_images * 1.05:
        log.warning("dataset cap: %d images is above max_images=%d - the required datasets and the per-family minimum "
                    "for attribution need that many", len(out), max_images)
    return out


def hard_cap(df: pd.DataFrame, max_images: int, seed: int) -> pd.DataFrame:
    """Strict version of cap_total: the result has AT MOST max_images rows (exactly max_images, rounded down to an even
    number, when there is enough data) - no exceptions for CIFAKE or attribution floors. Every (source, split) keeps
    real = AI and is shrunk by about the same fraction (largest-remainder allocation, at least 1 pair per group when
    the budget allows), each side stratified by generator."""
    if not max_images or len(df) <= max_images:
        return df
    groups = list(df.groupby(["source", "split"]))
    pairs = pd.Series({k: min(int((g.label == 0).sum()), int((g.label == 1).sum())) for k, g in groups})
    budget = max_images // 2                                   # pairs of (real, AI)
    base = pairs.clip(upper=1) if budget >= int((pairs > 0).sum()) else pairs * 0
    rest = budget - int(base.sum())
    extra_cap = pairs - base
    exact = extra_cap / max(1, int(extra_cap.sum())) * rest
    alloc = base + exact.astype(int)
    for k in (exact - exact.astype(int)).sort_values(ascending=False, kind="stable").index[: budget - int(alloc.sum())]:
        alloc[k] += 1
    alloc = alloc.clip(upper=pairs)
    parts = []
    for k, g in groups:
        n = int(alloc[k])
        if n:
            parts += [_stratified_sample(g[g.label == 1], n, seed), _stratified_sample(g[g.label == 0], n, seed)]
    out = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0]
    log.info("strict dataset cap: %d -> %d images (limit %d, all datasets shrunk proportionally)", len(df), len(out), max_images)
    return out


def check_balance(df: pd.DataFrame, report_path) -> None:
    """Verify (and record for the report) that real and AI images are balanced: equal counts in every source/split."""
    import json

    per_split = df.groupby(["split", "label"]).size().unstack(fill_value=0)
    per_source = df.groupby(["source", "split", "label"]).size().unstack(fill_value=0)
    for c in (0, 1):
        for t in (per_split, per_source):
            if c not in t.columns:
                t[c] = 0
    bad = per_source[per_source[0] != per_source[1]]
    if len(bad):
        raise SystemExit(f"balance check failed - real/AI counts differ:\n{bad}\nRebuild the manifest with --force.")
    gens = df[df.label == 1].groupby(["generator", "split"]).size().unstack(fill_value=0)
    rep = {"per_split": {s: {"real": int(r[0]), "ai": int(r[1])} for s, r in per_split.iterrows()},
           "per_source": {f"{src}/{sp}": {"real": int(r[0]), "ai": int(r[1])} for (src, sp), r in per_source.iterrows()},
           "ai_generators_per_split": {g: {k: int(v) for k, v in r.items()} for g, r in gens.iterrows()}}
    report_path.write_text(json.dumps(rep, indent=2))
    log.info("balance check passed (real = AI in every source and split): %s", rep["per_split"])


# ------------------------------------------------------------------------------------------- Kaggle (robust)
def _is_network_error(e: BaseException) -> bool:
    """Timeouts / dropped connections / 429 / 5xx - worth retrying. 404, auth errors and local file errors are not."""
    if isinstance(e, (FileExistsError, FileNotFoundError, PermissionError, IsADirectoryError, NotADirectoryError)):
        return False
    status = getattr(getattr(e, "response", None), "status_code", None)
    if status is not None:
        return status == 429 or status >= 500
    return isinstance(e, (TimeoutError, ConnectionError, OSError)) or "timed out" in str(e).lower()


def _disable_colab_cache(e: BaseException) -> None:
    """On Colab, kagglehub first asks Colab's local dataset-cache service (172.28.0.1:8011) to mount the dataset; that
    service sometimes does not answer (ReadTimeout after 15 s). DISABLE_COLAB_CACHE=1 makes kagglehub download
    directly from Kaggle instead (needs KAGGLE_USERNAME/KAGGLE_KEY, which the notebook sets). Read on every call."""
    import os
    if os.environ.get("DISABLE_COLAB_CACHE") != "1":
        os.environ["DISABLE_COLAB_CACHE"] = "1"
        log.warning("Kaggle: Colab's dataset cache did not answer (%s) - downloading directly from Kaggle from now on",
                    type(e).__name__)


def kaggle_retry(fn, what: str, attempts: int = 5):
    """fn() with retries on network errors (backoff 5, 10, 20, 40 s); the Colab cache is switched off after the first
    failure. Non-network errors are raised at once; the last network error is raised after `attempts` tries."""
    for a in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - classified below
            if not _is_network_error(e) or a == attempts - 1:
                raise
            _disable_colab_cache(e)
            wait = min(60, 5 * 2 ** a)
            log.warning("%s: %s (%s) - retry %d/%d in %d s", what, type(e).__name__, str(e)[:120], a + 1, attempts - 1, wait)
            time.sleep(wait)


def kaggle_download(handle: str, what: str, **kw) -> str:
    """kagglehub.dataset_download(handle, **kw) that survives Colab-cache timeouts and flaky connections."""
    import kagglehub
    return kaggle_retry(lambda: kagglehub.dataset_download(handle, **kw), what)


# ------------------------------------------------------------------------------------------- CIFAKE
CIFAKE_HANDLE = "birdy654/cifake-real-and-ai-generated-synthetic-images"


def prepare_cifake(ctx: Ctx, rng: random.Random) -> list[dict]:
    if ctx.args.cifake_root:
        root = Path(ctx.args.cifake_root)
    else:
        try:
            root = Path(kaggle_download(CIFAKE_HANDLE, "CIFAKE download"))
        except Exception as e:  # noqa: BLE001 - CIFAKE is mandatory: stop with a clear message, not a traceback
            raise SystemExit(f"CIFAKE: download from Kaggle failed ({type(e).__name__}: {str(e)[:200]}). Check the "
                             f"KAGGLE_USERNAME / KAGGLE_KEY secrets and the network, then re-run the same cell, or "
                             f"pass --cifake-root with a downloaded copy.") from e
    log.info("CIFAKE at %s", root)
    n = ctx.prof["cifake_per_class"]
    rows: list[dict] = []
    found = 0
    for part in (d for d in root.rglob("*") if d.is_dir() and d.name.lower() in {"train", "test"}):
        kids = {k.name.lower(): k for k in part.iterdir() if k.is_dir()}
        if not {"fake", "real"} <= kids.keys():
            continue
        found += 1
        cap = n if part.name.lower() == "train" else max(10, n // 4)
        for cls, label, gen in (("fake", 1, "stable-diffusion-v1.4"), ("real", 0, "cifar-10")):
            ps = _take(_images(kids[cls]), cap, rng)
            if part.name.lower() == "test":
                rows += _rows(ps, label, "CIFAKE", gen, "test")
            else:
                tmp = _rows(ps, label, "CIFAKE", gen, "train")
                for i, r in enumerate(tmp):
                    r["split"] = "val" if i < len(tmp) * 0.1 else "train"
                rows += tmp
    if not found:
        raise SystemExit(f"CIFAKE: no train/test folders with FAKE/REAL found under {root}")
    return rows


# ------------------------------------------------------------------------------------------- ArtiFact
ARTIFACT_HANDLE = "awsaf49/artifact-dataset"


class KaggleFiles:
    """Download SINGLE files of a Kaggle dataset into a folder on the work disk (Drive on Colab) instead of the whole
    archive. ArtiFact is tens of GB but we only use a few thousand images: this fetches its metadata.csv files plus
    exactly the sampled images. Files on Drive survive a new Colab runtime, so they are downloaded once.

    Uses kagglehub's public single-file download (dataset_download(handle, path=..., output_dir=...)) and, to find the
    sub-dataset folders, the Kaggle file-listing API that kagglehub itself uses. If that API is unavailable the caller
    falls back to the full download."""

    def __init__(self, handle: str, out: Path):
        from kagglehub.clients import build_kaggle_client
        from kagglehub.handle import parse_dataset_handle
        from kagglehub.http_resolver import _get_current_version

        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        with build_kaggle_client() as c:
            version = _get_current_version(c, parse_dataset_handle(handle))
        self.handle = f"{handle}/versions/{version}"   # pinned: same files on every resume, no version lookup per file

    def top_level(self) -> tuple[list[str], list[str]]:
        """(folders, files) at the dataset root."""
        from kagglehub.clients import build_kaggle_client
        from kagglehub.handle import parse_dataset_handle
        from kagglesdk.datasets.types.dataset_api_service import ApiListTreeDatasetFilesRequest

        h = parse_dataset_handle(self.handle)
        dirs, files, token = [], [], ""
        with build_kaggle_client() as c:
            for _ in range(100):
                r = ApiListTreeDatasetFilesRequest()
                r.owner_slug, r.dataset_slug, r.dataset_version_number = h.owner, h.dataset, h.version
                r.path, r.page_size = "", 200
                if token:
                    r.page_token = token
                resp = c.datasets.dataset_api_client.list_tree_dataset_files(r)
                dirs += [d.relative_url.strip("/") for d in resp.directories]
                files += [f.relative_url.strip("/") for f in resp.files]
                token = resp.next_page_token
                if not token:
                    break
        return sorted(dirs), sorted(files)

    def get(self, rel: str) -> Path | None:
        """Local path of dataset file `rel` (downloaded if needed); None if it does not exist on Kaggle."""
        import kagglehub

        dest = self.out / rel
        if dest.is_file() and dest.stat().st_size > 0:
            return dest
        for attempt in range(4):
            try:
                kagglehub.dataset_download(self.handle, path=rel, output_dir=str(self.out))
                return dest if dest.is_file() else None
            except FileExistsError:                    # left by an interrupted run -> replace it
                try:
                    kagglehub.dataset_download(self.handle, path=rel, output_dir=str(self.out), force_download=True)
                    return dest if dest.is_file() else None
                except Exception:  # noqa: BLE001
                    return None
            except Exception as e:  # noqa: BLE001
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status == 404:
                    return None
                if _is_network_error(e):
                    _disable_colab_cache(e)            # Colab cache timing out -> go direct for every later file
                time.sleep(3 * (attempt + 1) * (4 if status == 429 else 1))   # rate limit -> back off longer
        log.warning("ArtiFact: could not download %s", rel)
        return None

    def get_many(self, rels: list[str], workers: int = 8) -> list[Path | None]:
        import logging
        import os
        from concurrent.futures import ThreadPoolExecutor

        os.environ.setdefault("TQDM_DISABLE", "1")     # one progress bar per file would flood the Colab output
        logging.getLogger("kagglehub").setLevel(logging.WARNING)
        out: list[Path | None] = []
        with ThreadPoolExecutor(workers) as ex:
            for i, p in enumerate(ex.map(self.get, rels), 1):
                out.append(p)
                if i % 500 == 0:
                    log.info("ArtiFact: %d / %d files ready", i, len(rels))
        return out


def _artifact_frames(metas: list[Path]) -> list[pd.DataFrame]:
    # ArtiFact ships one metadata.csv PER SUB-DATASET (afhq/, big_gan/, coco/, ...). Reading only the first one would
    # use a single folder - often real-only, which balancing then drops entirely. Read and combine all of them.
    frames = []
    for meta in metas:
        m = pd.read_csv(meta)
        col = lambda *keys: next((c for c in m.columns if any(k in c.lower() for k in keys)), None)  # noqa: E731,B023
        cpath, clabel, ccat = col("path"), col("target", "label", "class"), col("category", "generator", "model")
        if not cpath or not clabel:
            log.warning("ArtiFact: %s has no path/label columns (%s) - skipped", meta, list(m.columns))
            continue
        lab = m[clabel]
        if lab.dtype == object:
            lab = lab.astype(str).str.lower().map(lambda v: 0 if v in {"real", "0", "factual", "nature"} else 1)
        frames.append(pd.DataFrame({"_rel": m[cpath].astype(str), "_label": lab.astype(int),
                                    "_cat": m[ccat].astype(str) if ccat else meta.parent.name, "_base": str(meta.parent)}))
    return frames


def prepare_artifact(ctx: Ctx, rng: random.Random) -> list[dict]:
    """ArtiFact, limited: only the metadata files and the sampled images are downloaded (into <work>/artifact on
    Drive), not the whole multi-GB archive. With --artifact-root an already-extracted copy is used instead."""
    n = ctx.prof["artifact_per_class"]
    if not n:
        return []
    kf: KaggleFiles | None = None
    if ctx.args.artifact_root:
        root = Path(ctx.args.artifact_root)
        metas = sorted(root.rglob("metadata.csv"))
    else:
        root = ctx.work / "artifact"
        try:
            kf = kaggle_retry(lambda: KaggleFiles(ARTIFACT_HANDLE, root), "ArtiFact version lookup")
            dirs, files = kaggle_retry(kf.top_level, "ArtiFact file list")
            want = (["metadata.csv"] if "metadata.csv" in files else []) + [f"{d}/metadata.csv" for d in dirs]
            log.info("ArtiFact: %d sub-datasets - downloading only their metadata and the sampled images into %s",
                     len(dirs), root)
            metas = [p for p in kf.get_many(want) if p]
        except Exception as e:  # noqa: BLE001
            if _is_network_error(e):              # Kaggle unreachable even after retries: ArtiFact is optional
                log.warning("ArtiFact: Kaggle not reachable (%s: %s) - ArtiFact skipped for this run (training "
                            "continues; re-run stage 1 with --force later to add it)", type(e).__name__, str(e)[:200])
                return []
            # listing API changed / old kagglehub -> full archive (slow, but works)
            log.warning("ArtiFact: per-file download unavailable (%s: %s) - downloading the FULL archive (tens of GB); "
                        "update kagglehub (pip install -U kagglehub) or pass --artifact-root to avoid this", type(e).__name__, e)
            try:
                kf, root = None, Path(kaggle_download(ARTIFACT_HANDLE, "ArtiFact full download"))
            except Exception as e2:  # noqa: BLE001
                log.warning("ArtiFact: full download failed too (%s: %s) - ArtiFact skipped for this run",
                            type(e2).__name__, str(e2)[:200])
                return []
            metas = sorted(root.rglob("metadata.csv"))
    if not metas:
        raise SystemExit(f"ArtiFact: metadata.csv not found under {root}. Look at the folder and adapt prepare_artifact().")
    frames = _artifact_frames(metas)
    if not frames:
        raise SystemExit(f"ArtiFact: no usable metadata.csv under {root} (need path + label columns)")
    df = pd.concat(frames, ignore_index=True)
    log.info("ArtiFact: %d metadata files, %d images listed (real %d / AI %d), %d categories", len(frames), len(df),
             int((df._label == 0).sum()), int((df._label == 1).sum()), df["_cat"].nunique())

    def candidates(rel: str, base: str) -> list[Path]:
        # metadata paths are relative to their sub-dataset folder or to the dataset root
        return list(dict.fromkeys([Path(base) / rel, root / rel]))

    def fetch(pairs: list[tuple[str, str]]) -> list[Path | None]:
        if kf is None:                                 # local copy: just look the files up
            return [next((p for p in candidates(r, b) if p.is_file()), None) for r, b in pairs]
        first = [candidates(r, b)[0] for r, b in pairs]
        got = kf.get_many([p.relative_to(root).as_posix() for p in first])
        retry = [i for i, p in enumerate(got) if p is None and len(candidates(*pairs[i])) > 1]
        if retry:
            alt = kf.get_many([candidates(*pairs[i])[1].relative_to(root).as_posix() for i in retry])
            for i, p in zip(retry, alt):
                got[i] = p
        return got

    probe = [p for p in fetch(list(zip(df["_rel"].head(3), df["_base"].head(3)))) if p]
    if not probe:
        raise SystemExit(f"ArtiFact: image paths from metadata.csv cannot be found (first: {df['_rel'].iloc[0]}).")
    rows: list[dict] = []
    for label in (0, 1):
        sub = df[df["_label"] == label]
        cats = sorted(sub["_cat"].unique())
        per = max(1, n // max(1, len(cats)))
        for cat in cats:
            g = sub[sub["_cat"] == cat].sample(frac=1.0, random_state=rng.randint(0, 10**6))
            have: list[Path] = []
            pos = 0
            while len(have) < per and pos < len(g):    # refill from the same category when a file is missing
                take = g.iloc[pos:pos + (per - len(have))]
                pos += len(take)
                have += [p for p in fetch(list(zip(take["_rel"], take["_base"]))) if p]
            rows += [{"path": str(p), "label": label, "source": "ArtiFact", "generator": cat, "split": "train",
                      "family": family_of(cat) if label == 1 else None, "attr_ok": True} for p in have[:per]]
    log.info("ArtiFact: %d images (real %d / AI %d)", len(rows), sum(r["label"] == 0 for r in rows),
             sum(r["label"] == 1 for r in rows))
    # stratified split: the same generator appears in every split (near-duplicates across splits are possible in
    # ArtiFact - that is why the unseen-generator Synthbuster test exists)
    _split_random(rows, rng)
    return rows


# ------------------------------------------------------------------------------------------- GenImage
def prepare_genimage(ctx: Ctx, rng: random.Random) -> list[dict]:
    n = ctx.prof["genimage_per_class"]
    if not n or not ctx.args.genimage_root:
        if n:
            log.warning("GenImage skipped: pass --genimage-root (it is hosted on Google Drive/Baidu, see docs/DATASETS.md)")
        return []
    root = Path(ctx.args.genimage_root)
    rows: list[dict] = []
    gens = [d for d in sorted(root.iterdir()) if d.is_dir()]
    if not gens:
        raise SystemExit(f"GenImage: no generator folders under {root}")
    for g in gens:
        ai = [p for p in _images(g) if "ai" in {x.lower() for x in p.relative_to(g).parts[:-1]}]
        real = [p for p in _images(g) if "nature" in {x.lower() for x in p.relative_to(g).parts[:-1]}]
        if not ai or not real:
            log.warning("GenImage: %s has ai=%d nature=%d - skipped (expected <gen>/{train,val}/{ai,nature}/...)", g.name, len(ai), len(real))
            continue
        k = max(1, n // len(gens))
        rows += _rows(_take(ai, k, rng), 1, "GenImage", g.name, "train")
        rows += _rows(_take(real, k, rng), 0, "GenImage", "imagenet", "train")
    if not rows:
        raise SystemExit("GenImage: nothing usable found - check the folder layout")
    _split_random(rows, rng)
    return rows


# ------------------------------------------------------------------------------------------- generator folders
def prepare_generator_folders(ctx: Ctx, rng: random.Random, root: Path, source: str, cap: int = 0,
                              strict: bool = True) -> list[dict]:
    """<root>/<generator>/*.png = AI images of that generator;  <root>/real/ (or nature/, laion/ ...) = real images.
    strict=False (optional datasets): return [] instead of stopping the run when nothing usable is found."""
    rows: list[dict] = []
    gens = [d for d in sorted(root.iterdir()) if d.is_dir()] if root.is_dir() else []
    if not gens:
        if not strict:
            return []
        raise SystemExit(f"{source}: no generator sub-folders under {root}")
    for g in gens:
        imgs = _take(_images(g), cap, rng)
        if not imgs:
            continue
        fam = family_of(g.name)
        rows += _rows(imgs, 0 if fam is None else 1, source, "real" if fam is None else g.name, "train")
    if not any(r["label"] == 1 for r in rows):
        if not strict:
            return []
        raise SystemExit(f"{source}: found no AI-generator folders under {root}")
    log.info("%s: %s", source, pd.DataFrame(rows).groupby(["generator", "label"]).size().to_dict())
    _split_random(rows, rng)
    return rows


# ------------------------------------------------------------------------------------------- OpenFake (Hugging Face)
_FAKE_WORDS = {"fake", "ai", "1", "synthetic", "generated", "ai-generated", "ai_generated", "true"}
_REAL_WORDS = {"real", "0", "authentic", "human", "photo", "false", "nature"}


def _safe_name(s) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in str(s)).strip("._")[:60]


def prepare_openfake(ctx: Ctx, rng: random.Random) -> list[dict]:
    """Stream OpenFake (https://huggingface.co/datasets/ComplexDataLab/OpenFake, config 'core') and keep a capped,
    family-balanced subset. Original file bytes are written untouched (re-encoding would change the very artefacts we
    study).

    OpenFake is an OPTIONAL extra: any failure (no network, gated dataset, schema change, connection dropped mid-way)
    is logged and the run continues with whatever was downloaded - it never aborts a multi-hour training run.
    The download is resumable: re-running continues where it stopped (files already on disk are not rewritten)."""
    cap = ctx.prof.get("openfake_per_family", 0)
    if not cap or ctx.args.no_openfake:
        return []
    root = ctx.work / "openfake"
    marker = root / "_COMPLETE"
    if marker.is_file():
        log.info("OpenFake already downloaded in %s - reusing", root)
        return _openfake_rows(ctx, rng, root)
    try:
        _download_openfake(ctx, root, cap)
        marker.write_text("ok")
    except Exception as e:  # noqa: BLE001 - optional dataset, never fatal
        log.warning("OpenFake download stopped early (%s: %s). Continuing with what is on disk; re-run stage 1 with "
                    "--force later to resume it, or pass --no-openfake.", type(e).__name__, e)
    return _openfake_rows(ctx, rng, root)


def _openfake_rows(ctx: Ctx, rng: random.Random, root: Path) -> list[dict]:
    if not root.is_dir() or not any(d.is_dir() for d in root.iterdir()):
        log.warning("OpenFake: nothing downloaded - skipped")
        return []
    rows = prepare_generator_folders(ctx, rng, root, "OpenFake", strict=False)
    if not rows:
        log.warning("OpenFake: downloaded folders contain no usable AI + real images - skipped")
    return rows


OPENFAKE_REPO = "datasets/ComplexDataLab/OpenFake"


def _http_status(e: BaseException) -> int | None:
    """HTTP status behind an exception raised anywhere in huggingface_hub / fsspec / pyarrow (None if not HTTP)."""
    import re
    seen, x = 0, e
    while x is not None and seen < 6:
        code = getattr(getattr(x, "response", None), "status_code", None)
        if code:
            return int(code)
        x, seen = (x.__cause__ or x.__context__), seen + 1
    m = re.search(r"\b(401|403|429)\b", str(e))
    return int(m.group(1)) if m else None


class _HubAccess:
    """Hugging Face access with automatic fallback - never crashes the run because of the token.

    * A token (Colab secret HF_TOKEN, env var, or huggingface-cli login) gives a free account its own, higher rate
      limit; without one, requests count against Colab's shared IP. Downloads of public datasets are free either way.
    * 401/403 (invalid / revoked / too-restricted token) -> the token is dropped and the download continues anonymously.
    * 429 (rate limit used up) -> switch token -> anonymous at once; if anonymous is limited as well, wait (server's
      Retry-After, else 1, 2, 4 ... max 10 min) and then try the token again (its 5-minute window has usually reset).
    The token itself is never logged."""

    def __init__(self):
        from huggingface_hub import HfFileSystem
        self._cls = HfFileSystem
        token = None
        try:
            from huggingface_hub import get_token
            token = get_token()
        except Exception:  # noqa: BLE001
            import os
            token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        self.token = token or None
        self.use_token = bool(self.token)
        self.waits = 0
        self.fs = self._make()
        log.info("OpenFake: Hugging Face access %s", "with your token (own rate limit)" if self.use_token
                 else "anonymous (no HF_TOKEN; shared Colab rate limit)")

    def _make(self):
        try:
            self._cls.clear_instance_cache()  # fsspec caches instances per argument set
        except Exception:  # noqa: BLE001
            pass
        return self._cls(token=self.token if self.use_token else False)

    def _switch(self, use_token: bool, why: str) -> None:
        self.use_token = use_token
        self.fs = self._make()
        log.warning("OpenFake: %s -> continuing %s", why, "with the token" if use_token else "WITHOUT the token")

    def handle(self, e: BaseException, deadline: float) -> bool:
        """True = the error was an access problem that is now dealt with -> retry the same request."""
        code = _http_status(e)
        if code in (401, 403) and self.use_token:
            self.token = None
            self._switch(False, f"token rejected (HTTP {code})")
            return True
        if code == 429:
            if self.use_token:
                self._switch(False, "rate limit of the token used up (HTTP 429)")
                return True
            headers = getattr(getattr(e, "response", None), "headers", None) or {}
            try:
                wait = float(headers.get("Retry-After", 0) or 0)
            except (TypeError, ValueError, AttributeError):
                wait = 0.0
            wait = min(600.0, max(wait, 60.0 * 2 ** min(self.waits, 4)))
            if time.monotonic() + wait > deadline:
                return False
            self.waits += 1
            log.warning("OpenFake: rate-limited without token too (HTTP 429) - waiting %.0f s", wait)
            time.sleep(wait)
            if self.token:
                self._switch(True, "rate-limit window over")
            return True
        return False


def _download_openfake(ctx: Ctx, root: Path, cap: int) -> None:
    """Low-memory OpenFake download (safe on free Colab, ~12 GB RAM).

    OpenFake's parquet files are ~5.7 GB with ~100 MB row groups of full-size images. `datasets` streaming (with a
    shuffle buffer) keeps thousands of images in RAM and crashed Colab. Instead the parquet files are read directly
    over HTTP range requests:
      1. read only the tiny `label` / `model` columns of a file and decide which rows are needed (family quotas);
      2. stream the `image` column of a row group in batches of 8 and write only the chosen rows to disk.
    Peak memory stays in the tens of MB, and row groups without any needed row are never downloaded."""
    import gc

    try:
        import pyarrow.parquet as pq
        import huggingface_hub  # noqa: F401
    except ImportError:
        raise RuntimeError("pyarrow / huggingface_hub missing (pip install -r requirements-train.txt)")
    from app.attribution import FAMILY_IDS

    config = getattr(ctx.args, "openfake_config", None) or "core"
    max_min = float(getattr(ctx.args, "openfake_max_minutes", 0) or 0) or float("inf")   # 0 = no limit
    t0 = time.monotonic()
    deadline = t0 + max_min * 60
    hub = _HubAccess()
    files: list[str] = []
    for attempt in range(8):
        try:
            files = sorted(hub.fs.glob(f"{OPENFAKE_REPO}/{config}/train-*.parquet"))
            break
        except Exception as e:  # noqa: BLE001
            if not hub.handle(e, deadline):
                if attempt >= 2:
                    raise
                time.sleep(10 * (attempt + 1))
    if not files:
        raise RuntimeError(f"no parquet files found for config '{config}'")
    random.Random(ctx.args.seed).shuffle(files)                    # deterministic -> resumable
    log.info("OpenFake: %d parquet files in config '%s' (reading label/model first, images only for kept rows)", len(files), config)

    quota = {f: cap for f in FAMILY_IDS}
    # as many real photos as fakes (GANs are absent from OpenFake, hence -1); balance() would otherwise throw away
    # the surplus AI images and with them the family balance
    quota["real"] = cap * max(1, len(FAMILY_IDS) - 1)
    got = {k: 0 for k in quota}
    max_bytes = float(getattr(ctx.args, "openfake_max_gb", 0) or 5) * 1e9
    min_free = float(getattr(ctx.args, "min_free_gb", 0) or 4) * 1e9
    max_scan = int(getattr(ctx.args, "openfake_max_scan", 0) or 600_000)
    stall_limit = 30_000                                           # families absent from OpenFake (e.g. GANs) never fill
    root.mkdir(parents=True, exist_ok=True)
    written = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    scanned = last_saved = skipped_label = 0
    stop = None
    fails = 0
    next_rg: dict[str, int] = {}  # a retried file continues at the row group where it stopped
    counted: set[str] = set()  # each saved image counts once, even when its row group is retried

    def classify(lab_raw, model_raw):
        lab = str(lab_raw).strip().lower()
        if lab in _FAKE_WORDS:
            model = str(model_raw or "")
            fam = family_of(model) or "other_ai"                   # a fake whose model name looks "real" is still AI
            gen = _safe_name(model) or "unknown_ai"
            if family_of(gen) is None:                             # the folder name must map back to an AI family
                gen = "ai_" + gen
            return (fam if fam in got else "other_ai"), gen
        if lab in _REAL_WORDS:
            return "real", "real"
        return None, None

    def allowed(fam: str) -> int:
        """Stratified under the time budget: a family may only fill its quota as fast as the clock runs (10 % at the
        start, 100 % at ~80 % of the budget), so common families cannot use up the time while rare ones wait. When
        the budget cuts the download, every family (and the real photos) is at about the same fraction of its quota,
        as far as OpenFake has the images."""
        if max_min == float("inf"):
            return quota[fam]
        frac = (time.monotonic() - t0) / (max_min * 60)
        return int(quota[fam] * min(1.0, 0.1 + 1.1 * frac))

    for fi, f in enumerate(files):
      if stop:
          break
      tries = 0
      while not stop:  # retry loop for one file (access problems / network hiccups)
        try:
            with hub.fs.open(f, "rb", block_size=4 << 20) as fh:
                pf = pq.ParquetFile(fh, pre_buffer=False, buffer_size=4 << 20)
                names = pf.schema_arrow.names
                low = {c.lower(): c for c in names}
                img_col = low.get("image")
                lab_col = next((low[k] for k in ("label", "target", "class", "is_fake") if k in low), None)
                mod_col = next((low[k] for k in ("model", "generator", "source_model", "model_name") if k in low), None)
                if not (img_col and lab_col and mod_col):
                    raise RuntimeError(f"expected image/label/model columns, found {names}")
                for rg in range(next_rg.get(f, 0), pf.metadata.num_row_groups):
                    meta = pf.read_row_group(rg, columns=[lab_col, mod_col]).to_pydict()
                    n = len(meta[lab_col])
                    scanned += n
                    picks: dict[int, tuple[str, str]] = {}
                    taking = {k: 0 for k in got}
                    paced = False
                    for i in range(n):
                        fam, gen = classify(meta[lab_col][i], meta[mod_col][i])
                        if fam is None:
                            skipped_label += 1
                        elif got[fam] + taking[fam] < allowed(fam):
                            picks[i] = (fam, gen)
                            taking[fam] += 1
                        elif got[fam] + taking[fam] < quota[fam]:
                            paced = True                   # held back by the pacing, not by the quota
                    if paced and not picks:
                        last_saved = scanned               # pacing is not a stall: the family is not exhausted
                    if picks:
                        offset = 0
                        for batch in pf.iter_batches(batch_size=8, row_groups=[rg], columns=[img_col]):
                            col = batch.column(0)
                            for j in range(len(col)):
                                i = offset + j
                                if i not in picks:
                                    continue
                                fam, gen = picks[i]
                                data, name = _image_bytes(col[j].as_py())
                                if not data:
                                    continue
                                ext = Path(name).suffix.lower()
                                if ext not in EXT:
                                    ext = _sniff_ext(data)
                                d = root / gen
                                d.mkdir(parents=True, exist_ok=True)
                                dest = d / f"{fi:04d}_{rg:03d}_{i:03d}{ext}"
                                if not dest.exists():              # resume: same seed -> same order -> same names
                                    if written + len(data) > max_bytes:
                                        stop = f"disk budget of {max_bytes / 1e9:.0f} GB reached (--openfake-max-gb)"
                                        break
                                    if got_total(got) % 200 == 0 and free_bytes(root) < min_free:
                                        stop = f"less than {min_free / 1e9:.0f} GB free on the work disk (--min-free-gb)"
                                        break
                                    tmp = dest.with_name(dest.name + ".part")
                                    tmp.write_bytes(data)
                                    tmp.replace(dest)
                                    written += len(data)
                                if str(dest) not in counted:
                                    counted.add(str(dest))
                                    got[fam] += 1
                                    last_saved = scanned
                                if got_total(got) % 1000 == 0:
                                    log.info("OpenFake progress: %s (%.1f GB, scanned %d rows, %.0f min)",
                                             got, written / 1e9, scanned, (time.monotonic() - t0) / 60)
                            offset += len(col)
                            del batch, col
                            if stop:
                                break
                        gc.collect()
                    if stop:
                        break
                    next_rg[f] = rg + 1
                    if avail_ram() < 1.5e9:
                        gc.collect()
                        if avail_ram() < 1.5e9:
                            stop = f"only {avail_ram() / 1e9:.1f} GB RAM left - stopping to protect the Colab session"
                            break
                    if all(got[k] >= quota[k] for k in quota):
                        stop = "all quotas filled"
                    elif scanned > max_scan:
                        stop = f"scanned {max_scan} rows (--openfake-max-scan)"
                    elif scanned - last_saved > stall_limit:
                        stop = f"nothing new in the last {stall_limit} rows - remaining families are rare/absent"
                    elif (time.monotonic() - t0) / 60 > max_min:
                        stop = (f"time budget of {max_min:.0f} min reached (--openfake-max-minutes) - stratified: "
                                f"each family filled to ~{min((got[k] / quota[k] for k in quota if got[k]), default=0) * 100:.0f}"
                                f"-{max(got[k] / quota[k] for k in quota) * 100:.0f} % of its quota")
                    if stop:
                        break
            fails = 0
            break  # file done
        except Exception as e:  # noqa: BLE001 - one unreadable file must not end the download
            if isinstance(e, RuntimeError) and "expected image/label/model" in str(e):
                raise
            if hub.handle(e, deadline):  # token rejected / rate limit -> retry this file
                continue
            if _http_status(e) == 429:
                stop = "rate limit not lifted before the time budget ran out"
                break
            tries += 1
            if tries < 3 and "magic bytes" not in str(e):
                log.warning("OpenFake: %s failed (%s: %s) - retrying", Path(f).name, type(e).__name__, e)
                time.sleep(10 * tries)
                continue
            fails += 1
            log.warning("OpenFake: skipped file %s (%s: %s)", Path(f).name, type(e).__name__, e)
            if fails >= 5:
                raise RuntimeError("5 files in a row failed - Hugging Face unreachable?") from e
            break
    log.info("OpenFake stopped: %s", stop or "all files read")
    if skipped_label:
        log.warning("OpenFake: %d rows had an unrecognised label value and were skipped", skipped_label)
    log.info("OpenFake done: %s (%.1f GB, scanned %d rows)", got, written / 1e9, scanned)


def avail_ram() -> float:
    """Available RAM in bytes (inf when psutil is missing)."""
    try:
        import psutil
        return float(psutil.virtual_memory().available)
    except Exception:  # noqa: BLE001
        return float("inf")


def got_total(got: dict) -> int:
    return sum(got.values())


def free_bytes(path: Path) -> float:
    """Free space on the disk holding `path` (on Colab's Drive mount this follows the Drive quota); inf if unknown."""
    import shutil
    try:
        p = path if path.exists() else path.parent
        return float(shutil.disk_usage(p).free)
    except Exception:  # noqa: BLE001
        return float("inf")


def _image_bytes(blob) -> tuple[bytes | None, str]:
    """HF image cell -> (original bytes, file name). Handles {'bytes','path'} dicts and decoded PIL images."""
    if blob is None:
        return None, ""
    if isinstance(blob, dict):
        data, name = blob.get("bytes"), str(blob.get("path") or "")
        if not data and name and Path(name).is_file():
            data = Path(name).read_bytes()
        return data, name
    if isinstance(blob, (bytes, bytearray)):
        return bytes(blob), ""
    if hasattr(blob, "save"):  # already-decoded PIL image: lossless PNG
        import io
        buf = io.BytesIO()
        blob.save(buf, format="PNG")
        return buf.getvalue(), "image.png"
    return None, ""


def _sniff_ext(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ".png"


# ------------------------------------------------------------------------------------------- RAISE (real camera photos, OOD)
def prepare_raise(ctx: Ctx, csv_path: Path) -> list[dict]:
    """RAISE ships as a CSV (RAISE_1k.csv / RAISE_2k.csv ...) with one row per photo and download URLs in the 'TIFF'
    (and 'NEF') columns - not as a folder of images. Download a capped random sample of the TIFFs, convert each to a
    lossless PNG (downscaled to --raise-max-side, 0 = keep full size) and return them as REAL rows for the
    unseen-generator test.

    Never fatal: an unreachable server or broken file is logged and skipped. Resumable: PNGs already on disk are reused."""
    import io
    from concurrent.futures import ThreadPoolExecutor, as_completed

    import numpy as np
    import requests
    from PIL import Image

    n = int(getattr(ctx.args, "raise_n", 0) or 300)
    max_side = int(getattr(ctx.args, "raise_max_side", 2048) or 0)
    out = ctx.work / "raise_real"
    out.mkdir(parents=True, exist_ok=True)
    try:
        df = pd.read_csv(csv_path, encoding="utf-8", encoding_errors="replace", dtype=str)
    except Exception as e:  # noqa: BLE001
        log.warning("RAISE: cannot read %s (%s) - OOD real images skipped", csv_path, e)
        return []
    df.columns = [str(c).strip() for c in df.columns]
    url_col = next((c for c in df.columns if c.lower() in {"tiff", "tif"}), None) or next(
        (c for c in df.columns
         if df[c].astype(str).str.strip().str.lower().str.contains(r"^https?://.*\.tiff?$", regex=True, na=False).any()), None)
    id_col = next((c for c in df.columns if c.lower() in {"file", "filename", "name", "id"}), None)
    if not url_col:
        log.warning("RAISE: no TIFF URL column in %s (columns: %s) - OOD real images skipped", csv_path, list(df.columns))
        return []
    df = df[df[url_col].astype(str).str.strip().str.match(r"^https?://", na=False)]
    df = df.sample(frac=1.0, random_state=ctx.args.seed).reset_index(drop=True)
    log.info("RAISE: %d photos listed in %s, using up to %d", len(df), csv_path.name, n)
    if df.empty:
        return []

    def dest_of(i: int) -> Path:
        s = _safe_name(df.at[i, id_col] if id_col else Path(str(df.at[i, url_col]).strip()).stem) or f"raise_{i}"
        return out / f"{s}.png"

    have = [dest_of(i) for i in range(len(df)) if dest_of(i).is_file()]
    todo = [i for i in range(len(df)) if not dest_of(i).is_file()]
    need = max(0, n - len(have))
    if need:
        log.info("RAISE: %d already on disk, downloading %d more (each TIFF is ~20-60 MB)", len(have), need)

    def fetch(i: int) -> Path | None:
        url, dest = str(df.at[i, url_col]).strip(), dest_of(i)
        for attempt in range(3):
            try:
                with requests.get(url, timeout=(20, 180), stream=True) as r:
                    r.raise_for_status()
                    buf = io.BytesIO()
                    for chunk in r.iter_content(1 << 20):
                        buf.write(chunk)
                buf.seek(0)
                with Image.open(buf) as im:
                    im.load()
                    if im.mode.startswith("I"):  # 16/32-bit TIFF -> 8-bit
                        a = np.asarray(im, dtype=np.float32)
                        im8 = Image.fromarray(np.clip(a / (float(a.max()) or 1.0) * 255, 0, 255).astype("uint8"))
                        rgb = im8.convert("RGB")
                    else:
                        rgb = im.convert("RGB")
                if max_side and max(rgb.size) > max_side:
                    s = max_side / max(rgb.size)
                    rgb = rgb.resize((max(1, round(rgb.width * s)), max(1, round(rgb.height * s))), Image.LANCZOS)
                tmp = dest.with_name(dest.name + ".part")
                rgb.save(tmp, format="PNG")
                tmp.replace(dest)
                return dest
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    log.warning("RAISE: %s failed (%s)", url, e)
        return None

    fails_in_row, pos, last_report = 0, 0, len(have)
    with ThreadPoolExecutor(4) as ex:
        while need > 0 and pos < len(todo) and fails_in_row < 12:
            batch = todo[pos:pos + min(need, 8)]
            pos += len(batch)
            for fut in as_completed([ex.submit(fetch, i) for i in batch]):
                p = fut.result()
                if p:
                    have.append(p)
                    need -= 1
                    fails_in_row = 0
                else:
                    fails_in_row += 1
            if len(have) - last_report >= 40:
                last_report = len(have)
                log.info("RAISE: %d / %d real photos ready", len(have), n)
    if fails_in_row >= 12:
        log.warning("RAISE: server looks unreachable (12 failures in a row) - continuing with %d photos", len(have))
    have = have[:n]
    log.info("RAISE: %d real camera photos for the OOD test", len(have))
    return _rows(have, 0, "RAISE", "camera", "ood")


# ------------------------------------------------------------------------------------------- Synthbuster (OOD test)
def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path, md5: str = "") -> bool:
    """Download with resume-safe temp file + up to 3 attempts; True when the file is on disk and (if given) md5 matches."""
    import requests

    if dest.is_file() and (not md5 or _md5(dest) == md5):
        return True
    for attempt in range(3):
        tmp = dest.with_name(dest.name + ".part")
        try:
            with requests.get(url, stream=True, timeout=(30, 300)) as r:
                r.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
            if md5 and _md5(tmp) != md5:
                raise IOError("checksum mismatch")
            tmp.replace(dest)
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("download %s failed (attempt %d/3): %s", dest.name, attempt + 1, e)
            tmp.unlink(missing_ok=True)
    return False


def prepare_synthbuster(ctx: Ctx) -> pd.DataFrame | None:
    """Unseen-generator (OOD) test set. Fetch the file list from Zenodo's API (so no file name is guessed), download,
    verify md5, unzip safely. Real camera photos come from --raise-csv (RAISE CSV) and/or --ood-real-dir (folder).

    Never fatal: the OOD set is an extra evaluation, so any problem is logged and the run continues without it."""
    out = ctx.work / "ood"
    out.mkdir(exist_ok=True)
    try:
        import requests
        rec = requests.get("https://zenodo.org/api/records/10066460", timeout=60).json()
        files = rec.get("files") or []
    except Exception as e:  # noqa: BLE001
        log.warning("Synthbuster: Zenodo not reachable (%s)", e)
        files = []
    if not files:
        log.warning("Synthbuster: no file list from Zenodo; using whatever is already in %s", out)
    for f in files:
        try:
            name = Path(f.get("key") or f.get("filename") or "synthbuster.bin").name
            url = (f.get("links") or {}).get("self") or (f.get("links") or {}).get("content")
            dest = out / name
            if not url:
                continue
            target = out / name[:-4] if name.endswith(".zip") else None
            if target is not None and (target / "_EXTRACTED").is_file():
                continue
            size = float(f.get("size") or 0)
            log.info("Synthbuster: %s (%.1f GB)", name, size / 1e9)
            need = size * (2.2 if target is not None else 1.1) + float(getattr(ctx.args, "min_free_gb", 4) or 4) * 1e9
            if not dest.is_file() and free_bytes(out) < need:
                log.warning("Synthbuster: %s needs ~%.0f GB free on the work disk (zip + extraction), only %.0f GB free - skipped",
                            name, need / 1e9, free_bytes(out) / 1e9)
                continue
            if not _download(url, dest, str(f.get("checksum", "")).replace("md5:", "")):
                log.warning("Synthbuster: giving up on %s", name)
                continue
            if target is not None:
                with zipfile.ZipFile(dest) as z:
                    for m in z.namelist():  # zip-slip guard
                        if not (target / m).resolve().is_relative_to(target.resolve()):
                            raise IOError(f"unsafe path in zip: {m}")
                    z.extractall(target)
                (target / "_EXTRACTED").write_text("ok")
                dest.unlink(missing_ok=True)  # free disk space (Drive quota)
        except Exception as e:  # noqa: BLE001
            log.warning("Synthbuster: skipped %s (%s)", f.get("key"), e)

    rows = []
    for p in _images(out):
        parts = p.relative_to(out).parts
        gen = parts[-2] if len(parts) > 1 else "synthbuster"
        if family_of(gen) is None:  # e.g. a 'raise' / 'real' folder inside the archive: those are real photos
            rows.append({"path": str(p), "label": 0, "source": "Synthbuster-real", "generator": "camera", "split": "ood",
                         "family": None, "attr_ok": False})
        else:
            rows.append({"path": str(p), "label": 1, "source": "Synthbuster", "generator": gen, "split": "ood",
                         "family": family_of(gen), "attr_ok": True})
    n_fake = sum(r["label"] == 1 for r in rows)
    log.info("Synthbuster: %d AI images found", n_fake)

    raise_csv = getattr(ctx.args, "raise_csv", None)
    real_dir = ctx.args.ood_real_dir
    if real_dir and Path(real_dir).is_file() and Path(real_dir).suffix.lower() == ".csv":
        raise_csv, real_dir = raise_csv or real_dir, None  # a RAISE CSV passed to --ood-real-dir by mistake
    if raise_csv:
        if Path(raise_csv).is_file():
            rows += prepare_raise(ctx, Path(raise_csv))
        else:
            log.warning("RAISE: --raise-csv %s not found - skipped", raise_csv)
    if real_dir:
        if Path(real_dir).is_dir():
            rows += _rows(_images(Path(real_dir))[:1000], 0, "OOD-real", "camera", "ood")
        else:
            log.warning("--ood-real-dir %s is not a folder - skipped", real_dir)
    if not n_fake:
        log.warning("OOD set has no AI images - skipped (evaluation runs without the unseen-generator test)")
        return None
    return pd.DataFrame(rows)
