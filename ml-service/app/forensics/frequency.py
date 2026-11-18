"""Hand-crafted frequency / noise-residual features (works at any resolution, CPU-cheap).

Generative up-sampling leaves periodic energy in the spectrum and changes the statistics of the
high-pass residual. These features feed a tiny MLP head (see training/05_train_frequency.py) and act as
the third, *independent* opinion in the ensemble next to the CLIP and CNN members.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

BINS = 32
N_FEATURES = BINS + 9 + 2  # radial spectrum + (std, skew, kurt) x RGB + 2 spectral summary stats
WIN = 256


def _crop(img: Image.Image) -> np.ndarray:
    w, h = img.size
    if min(w, h) < 64:  # too small for a meaningful spectrum
        s = 64 / min(w, h)
        img = img.resize((max(64, round(w * s)), max(64, round(h * s))), Image.BICUBIC)
        w, h = img.size
    side = min(WIN, w, h)
    side -= side % 2
    x, y = (w - side) // 2, (h - side) // 2
    return np.asarray(img.crop((x, y, x + side, y + side)), dtype=np.float32)


def _highpass(c: np.ndarray) -> np.ndarray:
    """4-neighbour Laplacian residual (suppresses image content, keeps pixel-level traces)."""
    p = np.pad(c, 1, mode="reflect")
    return 4 * p[1:-1, 1:-1] - p[:-2, 1:-1] - p[2:, 1:-1] - p[1:-1, :-2] - p[1:-1, 2:]


def _moments(r: np.ndarray) -> tuple[float, float, float]:
    sd = float(r.std()) + 1e-6
    z = (r - r.mean()) / sd
    return float(np.log(sd)), float((z ** 3).mean()), float((z ** 4).mean() - 3.0)


def features(img: Image.Image) -> np.ndarray:
    rgb = _crop(img.convert("RGB"))
    gray = rgb.mean(axis=2)
    res = _highpass(gray)
    n = res.shape[0]
    win = np.outer(np.hanning(n), np.hanning(n)).astype(np.float32)
    spec = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(res * win))))

    yy, xx = np.indices(spec.shape)
    rad = np.hypot(yy - n / 2, xx - n / 2) / (n / 2)             # 0 (DC) .. ~1 (Nyquist) .. 1.41 (corner)
    idx = np.minimum((rad * BINS).astype(int), BINS - 1)
    valid = rad <= 1.0
    radial = np.bincount(idx[valid], weights=spec[valid], minlength=BINS) / np.maximum(np.bincount(idx[valid], minlength=BINS), 1)
    radial = (radial - radial.mean()) / (radial.std() + 1e-6)

    mom = [m for ch in range(3) for m in _moments(_highpass(rgb[..., ch]))]

    core = spec[(rad > 0.06) & (rad <= 1.0)]
    peak = float(core.max() - np.median(core))                      # strong isolated peaks = periodic up-sampling grid
    hf = float(spec[(rad > 0.75) & (rad <= 1.0)].mean() / (core.mean() + 1e-6))

    out = np.concatenate([radial, np.asarray(mom), [peak, hf]]).astype(np.float32)
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
