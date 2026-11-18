"""Loads and integrity-checks a trained model bundle (the folder produced by training/08_export_bundle.py)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from app.detectors import fusion
from app.detectors.members import MEMBERS


class BundleError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Bundle:
    def __init__(self, root: Path):
        self.root = root
        cfg_path = root / "config.json"
        man_path = root / "manifest.json"
        if not cfg_path.is_file() or not man_path.is_file():
            raise BundleError("model bundle not found (config.json / manifest.json missing)")

        manifest: dict[str, str] = json.loads(man_path.read_text("utf-8"))["files"]
        for name, expected in manifest.items():
            p = (root / name).resolve()
            if root.resolve() not in p.parents or not p.is_file() or _sha256(p) != expected:
                raise BundleError(f"integrity check failed for {name!r} - bundle was modified or is incomplete")
        # one hash that identifies exactly these weights (stored with every analysis)
        self.weights_sha256 = hashlib.sha256("".join(f"{k}:{manifest[k]}" for k in sorted(manifest)).encode()).hexdigest()

        self.cfg: dict[str, Any] = json.loads(cfg_path.read_text("utf-8"))
        self.name = str(self.cfg.get("name", "hulagwai-ensemble"))
        self.version = str(self.cfg.get("version", "0.0.0"))
        self.thresholds = {**fusion.DEFAULT_THRESHOLDS, **self.cfg.get("thresholds", {})}
        self.fusion_cfg = self.cfg["fusion"]

        mpath = root / "metrics.json"
        self.metrics: dict[str, Any] | None = json.loads(mpath.read_text("utf-8")) if mpath.is_file() else None

        self.members = []
        for m in self.fusion_cfg["members"]:
            if m not in MEMBERS or m not in self.cfg:
                raise BundleError(f"unknown or unconfigured member {m!r}")
            self.members.append(MEMBERS[m](self.cfg[m], root))

    def logits(self, img: Image.Image) -> dict[str, float]:
        return {m.name: m.logit(img) for m in self.members}

    def roles(self) -> dict[str, str]:
        return {m.name: m.role for m in self.members}

    def info(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version, "weights_sha256": self.weights_sha256,
                "thresholds": self.thresholds, "metrics": self.metrics,
                "evaluated_at": (self.metrics or {}).get("generated_at")}
