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

# What each profile trains on. 'smoke' only proves the plumbing works (minutes, even on CPU).
PROFILES: dict[str, dict] = {
    "smoke": dict(cifake_per_class=60, artifact_per_class=0, genimage_per_class=0, cnn_epochs=1, cnn_batch=8, freq_max=200,
                  robustness_n=24, workers=0, pretrained=False, clip_epochs=60),
    "colab_fast": dict(cifake_per_class=40_000, artifact_per_class=15_000, genimage_per_class=15_000, cnn_epochs=3, cnn_batch=64,
                       freq_max=60_000, robustness_n=2_000, workers=2, pretrained=True, clip_epochs=300),
    "colab_full": dict(cifake_per_class=60_000, artifact_per_class=40_000, genimage_per_class=40_000, cnn_epochs=5, cnn_batch=64,
                       freq_max=120_000, robustness_n=4_000, workers=2, pretrained=True, clip_epochs=400),
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
    ap.add_argument("--ood-real-dir", help="folder of REAL camera photos for the unseen-generator test (e.g. RAISE-1k)")
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
