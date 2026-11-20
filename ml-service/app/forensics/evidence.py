"""Grounded evidence for "what makes it look AI" - computed locally from the same models, nothing invented.

What it CAN say: which independent analyses agreed, where in the picture the pixel-level detector fires hardest
(a heat map over native-resolution patches), which provenance markers the file carries, and what weakens the evidence.
What it CANNOT say: that "the hand has 8 fingers" or any other semantic defect - that would need a vision-language
model, and unverified free-text claims would be hallucinations. Regions are therefore labelled "where the detector
looks", not "verified defects".
"""
from __future__ import annotations

import base64
import io
from typing import Any

import numpy as np
from PIL import Image

from app import preprocess as P

MAX_GRID = 3
_V = ("upper", "middle", "lower")
_H = ("left", "centre", "right")


def _grid_positions(length: int, size: int) -> list[int]:
    n = 1 if length < 2 * size else 2 if length < 3 * size else MAX_GRID
    return [0] if n == 1 else [round(i * (length - size) / (n - 1)) for i in range(n)]


def _where(r: int, c: int, rows: int, cols: int) -> str:
    v = _V[0 if r == 0 else 2 if r == rows - 1 else 1] if rows > 1 else ""
    h = _H[0 if c == 0 else 2 if c == cols - 1 else 1] if cols > 1 else ""
    return f"{v}-{h}" if v and h else (v or h or "whole image")


def _colorize(scores: np.ndarray, size: tuple[int, int]) -> Image.Image:
    """scores in [0,1] -> RGBA overlay (transparent for low scores, warm colours for high)."""
    s = Image.fromarray((np.clip(scores, 0, 1) * 255).astype(np.uint8)).resize(size, Image.BILINEAR)
    a = np.asarray(s, dtype=np.float32) / 255.0
    r = np.clip(a * 2.0, 0, 1)
    g = np.clip(2.0 - a * 2.0, 0, 1) * np.clip(a * 3, 0, 1)
    out = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = (r * 255).astype(np.uint8), (g * 200).astype(np.uint8), 40
    out[..., 3] = (np.clip((a - 0.45) / 0.55, 0, 1) * 170).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def patch_map(img: Image.Image, cnn: Any, size: int = P.CROP) -> dict[str, Any] | None:
    """Score native-resolution patches with the CNN member.

    None when the image is smaller than one patch, or fits only ONE patch (a one-cell "map" would be a single
    colour and say nothing about location) - i.e. a heat map needs >= 448 px on at least one side.
    """
    w, h = img.size
    if min(w, h) < size:
        return None
    xs, ys = _grid_positions(w, size), _grid_positions(h, size)
    if len(xs) * len(ys) < 2:
        return None
    crops = [img.crop((x, y, x + size, y + size)) for y in ys for x in xs]
    z = np.asarray(cnn.patch_logits(crops), dtype=np.float64)
    p = (1 / (1 + np.exp(-np.clip(z, -30, 30)))).reshape(len(ys), len(xs))
    return {"rows": len(ys), "cols": len(xs), "scores": p, "xs": xs, "ys": ys, "size": size, "wh": (w, h)}


def overlay_jpeg_b64(img: Image.Image, pm: dict[str, Any], max_side: int = 480) -> str:
    """Patch scores (rows x cols) smoothly up-sampled over the whole image - no gaps between patches."""
    base = P.to_rgb(img).convert("RGBA")
    base.alpha_composite(_colorize(np.asarray(pm["scores"], dtype=np.float32), base.size))
    out = base.convert("RGB")
    out.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=78, optimize=True)   # fresh JPEG: no metadata carried over
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _strength(p: float) -> str:
    return "strong" if p >= 0.85 else "moderate" if p >= 0.65 else "weak"


def _flag(fid: str, category: str, strength: str, title: str, detail: str, source: str) -> dict[str, str]:
    return {"id": fid, "category": category, "strength": strength, "title": title, "detail": detail, "source": source}


_COMPONENT_TEXT = {
    "cnn": ("Pixel-level texture", "Fine texture and edge statistics resemble generated images (detector score {p:.0f}%)."),
    "frequency": ("Spectrum / noise pattern", "The frequency spectrum and noise residual show patterns typical of generator up-sampling ({p:.0f}%)."),
    "clip": ("Global look & style", "The overall appearance and feature statistics match known AI-generated images ({p:.0f}%)."),
}
_WARN_TEXT = {
    "low_resolution": "Very small image: little evidence available, the verdict is less reliable.",
    "upscaled_for_analysis": "Smaller than 224 px: enlarged for analysis, which weakens the pixel-level evidence.",
    "heavily_compressed": "Heavy JPEG compression hides fine artefacts and weakens the evidence.",
    "animated_first_frame_only": "Animated image: only the first frame was analysed.",
}


def build(components: dict[str, Any], meta: dict[str, Any], warnings: list[str], disagreement: float,
          pm: dict[str, Any] | None, p_ai: float) -> dict[str, Any]:
    flags: list[dict[str, str]] = []

    for f in meta.get("findings", []):
        if f.get("severity") == "strong_ai":
            flags.append(_flag("provenance_" + f["id"], "Provenance", "strong", f["title"], f.get("evidence", ""), "metadata"))

    if p_ai >= 0.5:
        for name, (cat, tmpl) in _COMPONENT_TEXT.items():
            c = components.get(name)
            if c and c["p"] >= 0.65:
                flags.append(_flag(f"signal_{name}", cat, _strength(c["p"]), cat + " signal", tmpl.format(p=c["p"] * 100), name))
        low = [n for n, c in components.items() if c["p"] < 0.4]
        if low and any(c["p"] >= 0.65 for c in components.values()):
            flags.append(_flag("mixed_signals", "Agreement", "weak", "Not every analysis agrees",
                               "These analyses did not flag the image: " + ", ".join(low) + ". Treat the verdict with extra care.", "ensemble"))
        elif components and disagreement <= 0.15 and p_ai >= 0.7:
            flags.append(_flag("all_agree", "Agreement", "moderate", "Independent analyses agree",
                               "All independent analyses point in the same direction.", "ensemble"))

    regions: list[dict[str, Any]] = []
    heat: dict[str, Any] = {"available": False}
    if pm is not None:
        sc, rows, cols = pm["scores"], pm["rows"], pm["cols"]
        w, h = pm["wh"]
        heat = {"available": True, "grid": [rows, cols], "scores": [[round(float(v), 3) for v in row] for row in sc]}
        order = np.dstack(np.unravel_index(np.argsort(-sc, axis=None), sc.shape))[0][:2]
        for r, c in order:
            s = float(sc[r, c])
            if s >= 0.6 and p_ai >= 0.5:
                regions.append({"x": round(pm["xs"][c] / w, 4), "y": round(pm["ys"][r] / h, 4), "w": round(pm["size"] / w, 4),
                                "h": round(pm["size"] / h, 4), "score": round(s, 3), "where": _where(int(r), int(c), rows, cols)})
        if regions:
            top = regions[0]
            flags.append(_flag("hot_region", "Location", _strength(top["score"]), f"Strongest signal: {top['where']} area",
                               f"The pixel-level detector scored this region {top['score'] * 100:.0f}% AI. "
                               "It shows where the model looks, not a verified defect.", "cnn"))
    for w_ in warnings:
        if w_ in _WARN_TEXT:
            flags.append(_flag("warn_" + w_, "Limitations", "weak", w_.replace("_", " ").capitalize(), _WARN_TEXT[w_], "quality"))

    return {
        "flags": flags[:12], "regions": regions, "heatmap": heat,
        "note": "These are signals from the detector models and the file itself. They do not identify specific visual defects "
                "such as extra fingers or garbled text, and a highlighted region is where the model looks, not proof of a flaw.",
    }
