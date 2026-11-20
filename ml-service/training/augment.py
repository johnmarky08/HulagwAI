"""Training-time degradations, applied identically to REAL and FAKE images.

Why: in public datasets the two classes often differ in *file format / compression* (e.g. GenImage: real = JPEG,
fake = PNG). A detector can then 'cheat' by learning the format instead of generator artefacts. Randomly
re-compressing / blurring / resizing both classes forces it to learn the real signal and makes it robust to
the screenshots, WhatsApp/Facebook recompression and resizes that real users upload.
"""
from __future__ import annotations

import io
import random

from PIL import Image, ImageFilter

from app import preprocess as P


def degrade(img: Image.Image, rng: random.Random, strength: float = 1.0) -> Image.Image:
    """JPEG is applied to most images (80 %): in OpenFake / GenImage the real photos are JPEG while most fakes are
    PNG, so with rarer JPEG the models learn "JPEG grid = real" - and real users mostly upload re-saved JPEGs of AI
    images. Compressing (almost) everything removes that shortcut and matches what the detector sees in production."""
    if rng.random() < 0.25 * strength:
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.1, 1.5)))
    if rng.random() < 0.35 * strength and min(img.size) >= 64:
        s = rng.uniform(0.5, 0.95)
        w, h = img.size
        small = img.resize((max(16, int(w * s)), max(16, int(h * s))), rng.choice([Image.BILINEAR, Image.BICUBIC, Image.LANCZOS]))
        img = small.resize((w, h), rng.choice([Image.BILINEAR, Image.BICUBIC])) if rng.random() < 0.5 else small
    if rng.random() < 0.80 * strength:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=rng.randint(60, 98))
        buf.seek(0)
        img = Image.open(buf).convert("RGB")
    return img


def random_native_crop(img: Image.Image, rng: random.Random, size: int = P.CROP) -> Image.Image:
    w, h = img.size
    if min(w, h) < size:
        s = size / min(w, h)
        img = img.resize((max(size, round(w * s)), max(size, round(h * s))), Image.BICUBIC)
        w, h = img.size
    x, y = rng.randint(0, w - size), rng.randint(0, h - size)
    c = img.crop((x, y, x + size, y + size))
    return c.transpose(Image.FLIP_LEFT_RIGHT) if rng.random() < 0.5 else c
