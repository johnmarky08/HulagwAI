"""Image preparation shared by the API and the training scripts (train/serve parity).

Design notes
------------
* AI-image detectors work on tiny, local, high-frequency traces. Resizing a large photo down to 224px
  erases most of them, so for images >= 224px we look at *native-resolution crops* (centre + corners)
  instead of resizing. Images smaller than 224px (e.g. CIFAKE's 32x32) have no choice but to be
  up-sampled; that case is flagged with a 'low_resolution' warning at inference time.
* Everything is converted to RGB first; transparency is flattened onto white.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
from PIL import Image

CLIP_MEAN = (0.48145466, 0.4578275, 0.40821073)
CLIP_STD = (0.26862954, 0.26130258, 0.27577711)
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

CROP = 224


def to_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGB":
        return img
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")


def native_crops(img: Image.Image, size: int = CROP, k: int = 5) -> list[Image.Image]:
    """Deterministic crops at native resolution (centre first, then the 4 quarter points)."""
    w, h = img.size
    if min(w, h) < size:  # too small: scale the short side up to `size`, then centre-crop
        scale = size / min(w, h)
        img = img.resize((max(size, round(w * scale)), max(size, round(h * scale))), Image.BICUBIC)
        w, h = img.size
    xs = [(w - size) // 2]
    ys = [(h - size) // 2]
    points = [(xs[0], ys[0])]
    if k > 1 and (w > size or h > size):
        qx = [(w - size) // 4, (w - size) * 3 // 4]
        qy = [(h - size) // 4, (h - size) * 3 // 4]
        points += [(x, y) for x in qx for y in qy]
    seen, out = set(), []
    for x, y in points[:k]:
        if (x, y) in seen:
            continue
        seen.add((x, y))
        out.append(img.crop((x, y, x + size, y + size)))
    return out


def crops_to_array(crops: Iterable[Image.Image], mean: tuple, std: tuple) -> np.ndarray:
    """-> float32 array [K, 3, H, W], normalised."""
    arr = np.stack([np.asarray(c, dtype=np.float32) / 255.0 for c in crops])  # K,H,W,3
    arr = (arr - np.asarray(mean, dtype=np.float32)) / np.asarray(std, dtype=np.float32)
    return np.ascontiguousarray(arr.transpose(0, 3, 1, 2))
