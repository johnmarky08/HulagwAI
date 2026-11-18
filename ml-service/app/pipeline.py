"""One image in -> one verdict out. Pure function of (bytes, loaded bundle)."""
from __future__ import annotations

import base64
import io
import time
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from app import preprocess as P
from app.config import Settings
from app.detectors import fusion
from app.detectors.bundle import Bundle
from app.forensics import metadata

Image.MAX_IMAGE_PIXELS = 40_000_000  # hard decompression-bomb limit inside Pillow itself
ALLOWED = {"JPEG", "PNG", "WEBP"}
ZERO_HASH = "0" * 64


class ImageError(ValueError):
    """The upload is not an acceptable image (maps to HTTP 422)."""


class ModelNotReady(RuntimeError):
    """No trained bundle is installed and metadata-only mode is off (maps to HTTP 503)."""


def _open(raw: bytes, s: Settings) -> Image.Image:
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()                                   # structural check; invalidates the handle
        img = Image.open(io.BytesIO(raw))
        if img.format not in ALLOWED:
            raise ImageError("unsupported image format")
        w, h = img.size
        if min(w, h) < 16 or max(w, h) > s.max_side or w * h > s.max_pixels:
            raise ImageError("image dimensions out of range")
        img.load()
        return img
    except ImageError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, SyntaxError) as e:
        raise ImageError("not a readable image") from e


def _jpeg_b64(img: Image.Image, max_side: int, quality: int) -> str:
    im = P.to_rgb(ImageOps.exif_transpose(img))
    im.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)   # fresh JPEG: no EXIF/XMP/ICC is carried over
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _warnings(img: Image.Image) -> list[str]:
    out = []
    if min(img.size) < 64:
        out.append("low_resolution")
    elif min(img.size) < P.CROP:
        out.append("upscaled_for_analysis")
    q = getattr(img, "quantization", None)
    if img.format == "JPEG" and q:
        avg = sum(q[0]) / len(q[0])
        if avg > 24:      # roughly JPEG quality < ~70
            out.append("heavily_compressed")
    if getattr(img, "n_frames", 1) > 1:
        out.append("animated_first_frame_only")
    return out


def analyze(raw: bytes, s: Settings, bundle: Bundle | None) -> dict[str, Any]:
    t0 = time.perf_counter()
    if bundle is None and not s.allow_metadata_only:
        raise ModelNotReady("model_not_ready")

    img = _open(raw, s)
    original_size = img.size
    meta = metadata.extract(raw, img)          # needs the un-converted image (info/exif chunks)
    warnings = _warnings(img)
    rgb = P.to_rgb(img)
    t_meta = time.perf_counter()

    components: dict[str, Any] = {}
    if bundle is not None:
        logits = bundle.logits(rgb)
        f = fusion.fuse(logits, bundle.fusion_cfg)
        for name, w in zip(bundle.fusion_cfg["members"], bundle.fusion_cfg["weights"]):
            components[name] = {"p": round(f["member_p"][name], 5), "logit": round(logits[name], 4),
                                "weight": round(float(w), 4), "role": bundle.roles()[name]}
        p, disagreement, thresholds = f["p"], f["disagreement"], bundle.thresholds
        model = {"name": bundle.name, "version": bundle.version, "weights_sha256": bundle.weights_sha256}
    else:
        warnings.append("no_ml_model")
        p, disagreement, thresholds = 0.5, 0.0, fusion.DEFAULT_THRESHOLDS
        model = {"name": "metadata-only", "version": "0", "weights_sha256": ZERO_HASH}
    t_model = time.perf_counter()

    d = fusion.decide(p, disagreement, thresholds, min(original_size), meta["strong_ai"])
    if meta["strong_ai"]:
        warnings.append("provenance_declares_ai")

    return {
        "model": model,
        "ai_probability": round(d["p"], 5),
        "confidence": round(d["confidence"], 5),
        "verdict": d["verdict"],
        "components": components,
        "metadata": {k: meta[k] for k in ("findings", "c2pa", "exif", "text_keys", "xmp_present") if k in meta},
        "warnings": warnings,
        "decision": {"source": d["source"], "disagreement": round(disagreement, 5), "widened_by": d["widened_by"], "bands": d["bands"]},
        "thresholds": {"real_max": d["bands"]["real_max"], "ai_min": d["bands"]["ai_min"]},
        "image": {"width": original_size[0], "height": original_size[1], "format": img.format, "mode": img.mode},
        "preview_jpeg_b64": _jpeg_b64(img, 1024, 85),
        "thumb_jpeg_b64": _jpeg_b64(img, 480, 80),
        "timings_ms": {"metadata": round((t_meta - t0) * 1000), "model": round((t_model - t_meta) * 1000),
                       "total": round((time.perf_counter() - t0) * 1000)},
    }
