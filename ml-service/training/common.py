"""Shared plumbing for the training pipeline (runs on Google Colab; also works on any CUDA/CPU machine)."""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `import app...` work
from app import preprocess as P  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("train")
for _noisy in ("httpx", "httpx2", "httpcore", "httpcore2", "huggingface_hub", "fsspec", "urllib3", "filelock", "datasets"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)   # one INFO line per HTTP request floods the Colab output


class _NoHttpChatter(logging.Filter):
    """Drop per-request HTTP lines whatever the client library's logger is called (httpx, httpx2, ...)."""
    def filter(self, record: logging.LogRecord) -> bool:
        return not (record.levelno < logging.WARNING and str(record.msg).startswith("HTTP Request"))


for _h in logging.getLogger().handlers:
    _h.addFilter(_NoHttpChatter())

# What each profile trains on. 'smoke' only proves the plumbing works (minutes, even on CPU).
PROFILES: dict[str, dict] = {
    "smoke": dict(cifake_per_class=60, artifact_per_class=0, genimage_per_class=0, cnn_epochs=1, cnn_batch=8, freq_max=200,
                  robustness_n=24, workers=0, pretrained=False, clip_epochs=60,
                  openfake_per_family=0, attr_epochs=150, attr_min=4),
    # CIFAKE is kept small on purpose: 32x32 images from one 2022 generator are easy and unlike real uploads; when they
    # made up half the data they also dominated validation, i.e. the fusion weights and thresholds. The capacity goes
    # to ArtiFact (25 generators) and OpenFake (current generators: FLUX, Midjourney 6/7, DALL-E 3, GPT Image, Imagen).
    "colab_fast": dict(cifake_per_class=10_000, artifact_per_class=20_000, genimage_per_class=15_000, cnn_epochs=4, cnn_batch=64,
                       freq_max=60_000, robustness_n=2_000, workers=2, pretrained=True, clip_epochs=300,
                       openfake_per_family=4_000, attr_epochs=300, attr_min=60),
    "colab_full": dict(cifake_per_class=15_000, artifact_per_class=40_000, genimage_per_class=40_000, cnn_epochs=6, cnn_batch=64,
                       freq_max=120_000, robustness_n=4_000, workers=2, pretrained=True, clip_epochs=400,
                       openfake_per_family=8_000, attr_epochs=400, attr_min=60),
}


@dataclass
class Ctx:
    work: Path
    profile_name: str
    prof: dict
    args: argparse.Namespace
    device: str = "cpu"
    paths: dict = field(default_factory=dict)

    @property
    def manifest(self) -> Path: return self.work / "manifest.csv"
    @property
    def features(self) -> Path: return self.work / "features"
    @property
    def artifacts(self) -> Path: return self.work / "artifacts"
    @property
    def reports(self) -> Path: return self.work / "reports"
    @property
    def clip_cfg(self) -> dict:
        return {"arch": self.args.clip_arch, "pretrained": "openai" if self.prof["pretrained"] else None, "crop": P.CROP, "k_crops": 5}
    @property
    def cnn_cfg(self) -> dict:
        return {"arch": self.args.cnn_arch, "crop": P.CROP, "k_crops": 5}


def parse(description: str, extra=None) -> Ctx:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--work", default=os.environ.get("HULAGWAI_WORK", "work"), help="working folder (use Google Drive on Colab)")
    ap.add_argument("--profile", default="colab_fast", choices=sorted(PROFILES))
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--clip-arch", default="ViT-B-16", help="ViT-B-16 (default, light) or ViT-L-14 (better, ~3x slower on CPU)")
    ap.add_argument("--cnn-arch", default="convnext_tiny")
    ap.add_argument("--cifake-root", help="skip kagglehub and use this folder (contains train/ and test/)")
    ap.add_argument("--artifact-root", help="folder of the extracted ArtiFact dataset")
    ap.add_argument("--genimage-root", help="folder of the downloaded GenImage subset (see docs/DATASETS.md)")
    ap.add_argument("--generator-root", help="folder with one sub-folder per generator (e.g. midjourney-6/, flux-dev/) and an optional real/ folder")
    ap.add_argument("--no-openfake", action="store_true", help="do not download OpenFake (generator-labelled images from Hugging Face)")
    ap.add_argument("--openfake-config", default="core", help="OpenFake config: core (default), supplement_t2i, ...")
    ap.add_argument("--openfake-max-scan", type=int, default=600_000, help="stop streaming OpenFake after this many rows")
    ap.add_argument("--openfake-max-minutes", type=float, default=120, help="time budget for the OpenFake download")
    ap.add_argument("--openfake-max-gb", type=float, default=25, help="disk budget for the OpenFake images (they are stored in --work, i.e. on Drive)")
    ap.add_argument("--min-free-gb", type=float, default=4, help="stop optional downloads when less than this is free on the --work disk")
    ap.add_argument("--ood-real-dir", help="folder of REAL camera photos for the unseen-generator test")
    ap.add_argument("--raise-csv", help="RAISE CSV (e.g. RAISE_2k.csv) - its TIFF URLs are downloaded as real photos for the unseen-generator test")
    ap.add_argument("--raise-n", type=int, default=300, help="how many RAISE photos to download (each TIFF is ~20-60 MB)")
    ap.add_argument("--raise-max-side", type=int, default=2048, help="downscale RAISE photos to this longest side (0 = keep full size)")
    ap.add_argument("--with-ood", action="store_true", help="download Synthbuster (unseen generators) for the final evaluation")
    ap.add_argument("--force", action="store_true", help="redo this stage even if its output exists")
    if extra:
        extra(ap)
    args = ap.parse_args()

    random.seed(args.seed); np.random.seed(args.seed)
    device = "cpu"
    try:
        import torch
        torch.manual_seed(args.seed)
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        pass
    ctx = Ctx(Path(args.work).resolve(), args.profile, PROFILES[args.profile], args, device)
    for d in (ctx.work, ctx.features, ctx.artifacts, ctx.reports):
        d.mkdir(parents=True, exist_ok=True)
    log.info("profile=%s device=%s work=%s", ctx.profile_name, device, ctx.work)
    return ctx


def load_manifest(ctx: Ctx) -> pd.DataFrame:
    if not ctx.manifest.is_file():
        raise SystemExit("manifest.csv missing - run training.01_prepare_data first")
    return pd.read_csv(ctx.manifest)


def open_rgb(path: str) -> Image.Image | None:
    """Open one training image; corrupt files return None instead of killing a 6-hour run."""
    try:
        with Image.open(path) as im:
            im.load()
            return P.to_rgb(im).copy()
    except Exception:
        return None


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def done(path: Path, ctx: Ctx) -> bool:
    if path.exists() and not ctx.args.force:
        log.info("%s already exists - skipping (use --force to redo)", path.name)
        return True
    return False


def run_info(ctx: Ctx) -> dict:
    """Everything needed to reproduce / audit a training run."""
    import platform
    import subprocess
    from datetime import datetime, timezone
    from importlib import metadata

    pk = {}
    for n in ("torch", "torchvision", "timm", "open_clip_torch", "scikit-learn", "numpy", "pandas", "Pillow", "safetensors", "kagglehub"):
        try:
            pk[n] = metadata.version(n)
        except metadata.PackageNotFoundError:
            pk[n] = None
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        commit = None
    return {"created_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(), "platform": platform.platform(),
            "device": ctx.device, "profile": ctx.profile_name, "profile_settings": ctx.prof, "seed": ctx.args.seed,
            "clip": ctx.clip_cfg, "cnn": ctx.cnn_cfg, "git_commit": commit, "packages": pk,
            "command": "python -m training.run_all --profile %s --seed %s --version %s" % (ctx.profile_name, ctx.args.seed, ctx.args.version)}
