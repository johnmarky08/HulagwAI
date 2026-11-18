"""Dataset adapters -> one manifest.csv (path,label,source,generator,split). label: 1 = AI-generated, 0 = real.

CIFAKE's layout is well known. ArtiFact / GenImage / Synthbuster adapters were written from their public
documentation and verify what they find at run time (they print counts and stop with a clear message if
the folder layout is not what is expected) - because I could not download them while writing this.
"""
from __future__ import annotations

import hashlib
import random
import zipfile
from pathlib import Path

import pandas as pd

from .common import Ctx, log

EXT = {".jpg", ".jpeg", ".png", ".webp"}

DATASETS_INFO = [
    {"name": "CIFAKE", "role": "training (baseline) + test", "url": "https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images"},
    {"name": "ArtiFact", "role": "training + test (25 generators)", "url": "https://github.com/awsaf49/artifact"},
    {"name": "GenImage", "role": "training + test (subset)", "url": "https://github.com/GenImage-Dataset/GenImage"},
    {"name": "Synthbuster", "role": "unseen-generator test only", "url": "https://zenodo.org/records/10066460"},
]


def _images(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXT)


def _take(items: list, n: int, rng: random.Random) -> list:
    items = list(items)
    rng.shuffle(items)
    return items[:n] if n else items


def _rows(paths, label, source, generator, split) -> list[dict]:
    return [{"path": str(p), "label": label, "source": source, "generator": generator, "split": split} for p in paths]


def _split_random(rows: list[dict], rng: random.Random, val=0.1, test=0.1) -> None:
    rng.shuffle(rows)
    n = len(rows)
    for i, r in enumerate(rows):
        r["split"] = "test" if i < n * test else "val" if i < n * (test + val) else "train"


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
                    picked.append({"path": str(p), "label": label, "source": "ArtiFact", "generator": cat, "split": "train"})
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


# ------------------------------------------------------------------------------------------- Synthbuster (OOD test)
def prepare_synthbuster(ctx: Ctx) -> pd.DataFrame | None:
    """Fetch the file list from Zenodo's API (so no file name is guessed), download, verify md5, unzip safely."""
    import requests

    out = ctx.work / "ood"
    out.mkdir(exist_ok=True)
    rec = requests.get("https://zenodo.org/api/records/10066460", timeout=60).json()
    files = rec.get("files") or []
    if not files:
        log.warning("Synthbuster: Zenodo returned no files; skipping OOD set")
        return None
    for f in files:
        name = Path(f.get("key") or f.get("filename") or "synthbuster.bin").name
        url = (f.get("links") or {}).get("self")
        dest = out / name
        if not url:
            continue
        if not dest.exists():
            log.info("downloading %s (%.1f GB)", name, (f.get("size") or 0) / 1e9)
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with dest.open("wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
        md5 = str(f.get("checksum", "")).replace("md5:", "")
        if md5:
            h = hashlib.md5()
            with dest.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != md5:
                raise SystemExit(f"Synthbuster: checksum mismatch for {name}")
        if name.endswith(".zip"):
            with zipfile.ZipFile(dest) as z:
                for m in z.namelist():            # zip-slip guard
                    if not (out / m).resolve().is_relative_to(out.resolve()):
                        raise SystemExit("unsafe path in zip")
                z.extractall(out / name[:-4])
    rows = []
    for p in _images(out):
        parts = p.relative_to(out).parts
        gen = parts[-2] if len(parts) > 1 else "synthbuster"
        rows.append({"path": str(p), "label": 1, "source": "Synthbuster", "generator": gen, "split": "ood"})
    if ctx.args.ood_real_dir:
        rows += _rows(_images(Path(ctx.args.ood_real_dir))[:1000], 0, "OOD-real", "camera", "ood")
    return pd.DataFrame(rows) if rows else None
