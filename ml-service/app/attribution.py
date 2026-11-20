"""Which AI family made the image?  (closed-set classifier + honest "unknown")

Families, not versions: Midjourney v6 vs v7 is far less reliable than Midjourney vs FLUX. A trained attribution head
can only name families it saw in training; anything else must come out as "unknown" - the abstention threshold
`tau` is fitted on validation data (training/06b_train_attribution.py).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
from safetensors.numpy import load_file as load_np

FAMILIES: dict[str, str] = {
    "stable_diffusion": "Stable Diffusion (1.x / 2.x)",
    "sdxl_sd3": "SDXL / Stable Diffusion 3",
    "flux": "FLUX",
    "midjourney": "Midjourney",
    "dalle": "DALL·E",
    "gpt_image": "GPT Image (OpenAI)",
    "google": "Google Imagen / Gemini",
    "gan": "GAN (StyleGAN, BigGAN …)",
    "other_ai": "Other AI generator",
}
FAMILY_IDS = list(FAMILIES)

_REAL = re.compile(r"^(real|nature|laion|pexels|docci|imagenet|reddit[-_ ]?real|camera|raise.*)$", re.I)
_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"sd[-_ ]?xl|sdxl|stable[-_ ]?diffusion[-_ ]?(xl|3)|sd[-_ ]?3"), "sdxl_sd3"),
    (re.compile(r"stable[-_ ]?diffusion|(^|[^a-z])sd[-_ ]?(v?1|v?2|1\.|2\.)|sdv[0-9]|latent[-_ ]?diffusion"), "stable_diffusion"),
    (re.compile(r"flux"), "flux"),
    (re.compile(r"midjourney|(^|[^a-z])mj[-_ ]?v?[0-9]"), "midjourney"),
    (re.compile(r"dall[-_ ·.]?e"), "dalle"),
    (re.compile(r"gpt[-_ ]?image|gpt[-_ ]?4o|gpt4o|(^|[^a-z])sora"), "gpt_image"),
    (re.compile(r"imagen|nano[-_ ]?banana|gemini"), "google"),
    (re.compile(r"(^|[^a-z])(big|style|pro|projected|cycle|star|gau)?gan([^a-z]|$)"), "gan"),
]


def family_of(name: str | None) -> str | None:
    """Raw dataset generator name -> family id.  None = not an AI image (real source)."""
    if not name:
        return None
    n = str(name).strip().lower()
    if _REAL.match(n):
        return None
    for rx, fam in _RULES:
        if rx.search(n):
            return fam
    return "other_ai"


class AttributionHead:
    """Softmax-linear head on [CLIP embedding ‖ CNN embedding]; pure numpy at inference."""

    def __init__(self, cfg: dict[str, Any], root: Path):
        d = load_np(str(root / "attribution_head.safetensors"))
        self.w, self.b = d["weight"].astype(np.float32), d["bias"].astype(np.float32)
        self.families: list[str] = list(cfg["families"])
        self.inputs: list[str] = list(cfg.get("inputs", ["clip", "cnn"]))
        self.tau = float(cfg.get("tau", 0.5))
        self.temperature = float(cfg.get("temperature", 1.0))
        if self.w.shape[0] != len(self.families):
            raise ValueError("attribution head does not match its family list")

    def predict(self, feats: dict[str, np.ndarray | None]) -> dict[str, Any]:
        parts = [feats.get(n) for n in self.inputs]
        if any(p is None for p in parts):
            return {"available": False, "reason": "features_missing"}
        x = np.concatenate(parts).astype(np.float32)
        if x.shape[0] != self.w.shape[1]:
            return {"available": False, "reason": "feature_size_mismatch"}
        z = (self.w @ x + self.b) / max(self.temperature, 1e-3)
        z -= z.max()
        p = np.exp(z) / np.exp(z).sum()
        order = np.argsort(-p)[:3]
        top = [{"family": self.families[i], "label": FAMILIES.get(self.families[i], self.families[i]), "p": round(float(p[i]), 4)} for i in order]
        known = top[0]["p"] >= self.tau
        return {"available": True, "source": "model", "decision": "family" if known else "unknown", "top": top, "tau": self.tau}
