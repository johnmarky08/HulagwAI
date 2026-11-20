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
    rng.shuffle(rows)
    n = len(rows)
    for i, r in enumerate(rows):
        r["split"] = "test" if i < n * test else "val" if i < n * (test + val) else "train"


def dedup_and_check_leakage(df: pd.DataFrame, report_path) -> pd.DataFrame:
    """Data-leakage guard: the SAME image (byte-identical, SHA-256) must never sit in two splits.

    * duplicate across splits  -> kept in the 'strongest' split only (train > val > test), removed elsewhere
    * duplicate inside a split -> kept once
    * same bytes labelled both real and fake -> dropped entirely (label noise)
    Near-duplicates (resized/re-encoded copies) are NOT detected; this limitation is documented in the model card.
    """
    import json
    from concurrent.futures import ThreadPoolExecutor

    def h(path: str) -> str:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    with ThreadPoolExecutor(8) as ex:
        df = df.assign(sha=list(ex.map(h, df["path"])))
    before = len(df)
    conflict = df.groupby("sha")["label"].nunique()
    conflict_hashes = set(conflict[conflict > 1].index)
    df = df[~df["sha"].isin(conflict_hashes)]
    rank = {"train": 0, "val": 1, "test": 2}
    df = df.assign(_r=df["split"].map(rank)).sort_values("_r", kind="stable")
    cross = df.groupby("sha")["split"].nunique()
    n_cross = int((cross > 1).sum())
    df = df.drop_duplicates("sha", keep="first").drop(columns="_r")
    rep = {"images_before": before, "label_conflicts_removed": len(conflict_hashes), "hashes_in_multiple_splits": n_cross,
           "images_after": len(df), "removed_total": before - len(df)}
    report_path.write_text(json.dumps(rep, indent=2))
    log.info("leakage check: %s", rep)
    return df.drop(columns="sha")


def balance(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Within every (source, split) keep as many real as fake images -> the model cannot use the 'source' as a clue."""
    parts = []
    for _, g in df.groupby(["source", "split"]):
        n = g["label"].value_counts()
        k = int(n.min()) if len(n) == 2 else 0
        for _, gl in g.groupby("label"):
            parts.append(gl.sample(n=min(k, len(gl)), random_state=seed))
    return pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0]


# ------------------------------------------------------------------------------------------- CIFAKE
def prepare_cifake(ctx: Ctx, rng: random.Random) -> list[dict]:
    if ctx.args.cifake_root:
        root = Path(ctx.args.cifake_root)
    else:
        import kagglehub
        root = Path(kagglehub.dataset_download("birdy654/cifake-real-and-ai-generated-synthetic-images"))
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
def prepare_artifact(ctx: Ctx, rng: random.Random) -> list[dict]:
    n = ctx.prof["artifact_per_class"]
    if not n:
        return []
    if ctx.args.artifact_root:
        root = Path(ctx.args.artifact_root)
    else:
        import kagglehub
        log.warning("ArtiFact is LARGE (tens of GB). On Colab make sure Drive/disk has room, or pass --artifact-root.")
        root = Path(kagglehub.dataset_download("awsaf49/artifact-dataset"))
    metas = sorted(root.rglob("metadata.csv"))
    if not metas:
        raise SystemExit(f"ArtiFact: metadata.csv not found under {root}. Look at the folder and adapt prepare_artifact().")
    df = pd.read_csv(metas[0])
    log.info("ArtiFact metadata columns: %s", list(df.columns))
    col = lambda *keys: next((c for c in df.columns if any(k in c.lower() for k in keys)), None)  # noqa: E731
    cpath, clabel, ccat = col("path"), col("target", "label", "class"), col("category", "generator", "model")
    if not cpath or not clabel:
        raise SystemExit(f"ArtiFact: cannot find path/label columns in {list(df.columns)}")
    lab = df[clabel]
    if lab.dtype == object:
        lab = lab.astype(str).str.lower().map(lambda v: 0 if v in {"real", "0", "factual", "nature"} else 1)
    df = df.assign(_label=lab.astype(int), _cat=df[ccat].astype(str) if ccat else "artifact")

    def resolve(rel: str) -> Path | None:
        for base in (metas[0].parent, root):
            p = base / rel
            if p.is_file():
                return p
        return None

    probe = [resolve(str(r)) for r in df[cpath].head(5)]
    if not any(probe):
        raise SystemExit(f"ArtiFact: image paths from metadata.csv do not exist under {root} (first: {df[cpath].iloc[0]}).")
    rows: list[dict] = []
    for label in (0, 1):
        sub = df[df["_label"] == label]
        cats = sorted(sub["_cat"].unique())
        per = max(1, n // max(1, len(cats)))
        picked: list[dict] = []
        for cat in cats:
            g = sub[sub["_cat"] == cat]
            for rel in g[cpath].sample(n=min(per, len(g)), random_state=rng.randint(0, 10**6)):
                p = resolve(str(rel))
                if p:
                    picked.append({"path": str(p), "label": label, "source": "ArtiFact", "generator": cat, "split": "train",
                                   "family": family_of(cat) if label == 1 else None, "attr_ok": True})
        rows += picked
    # split by generator group so the same generator appears in every split (near-duplicates across splits are possible
    # in ArtiFact - that is why the unseen-generator Synthbuster test exists)
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
    max_min = float(getattr(ctx.args, "openfake_max_minutes", 0) or 120)
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
    max_bytes = float(getattr(ctx.args, "openfake_max_gb", 0) or 25) * 1e9
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
                    for i in range(n):
                        fam, gen = classify(meta[lab_col][i], meta[mod_col][i])
                        if fam is None:
                            skipped_label += 1
                        elif got[fam] + sum(1 for v in picks.values() if v[0] == fam) < quota[fam]:
                            picks[i] = (fam, gen)
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
                        stop = f"time budget of {max_min:.0f} min reached (--openfake-max-minutes)"
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
