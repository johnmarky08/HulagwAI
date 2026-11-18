import io
import json
import sys

import numpy as np
import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from app.detectors import fusion
from app.forensics import frequency, metadata
from tests.conftest import make_image
from training import metrics as M


# ---------------------------------------------------------------- metadata forensics
def _png_with_text(**chunks) -> bytes:
    info = PngInfo()
    for k, v in chunks.items():
        info.add_text(k, v)
    buf = io.BytesIO()
    Image.fromarray(np.zeros((32, 32, 3), np.uint8)).save(buf, "PNG", pnginfo=info)
    return buf.getvalue()


def test_detects_stable_diffusion_parameters():
    raw = _png_with_text(parameters="a cat\nNegative prompt: bad\nSteps: 20, Sampler: Euler a, CFG scale: 7, Seed: 1")
    out = metadata.extract(raw, Image.open(io.BytesIO(raw)))
    assert out["strong_ai"] and any(f["id"] == "sd_webui_parameters" for f in out["findings"])


def test_detects_comfyui_and_software_tag():
    raw = _png_with_text(prompt='{"3": {"class_type": "KSampler"}}', Software="NovelAI")
    out = metadata.extract(raw, Image.open(io.BytesIO(raw)))
    ids = {f["id"] for f in out["findings"]}
    assert {"comfyui_graph", "text_chunk_ai"} <= ids


def test_c2pa_ai_claim_and_plain_c2pa():
    plain = make_image("PNG") + b"jumb c2pa manifest"
    out = metadata.extract(plain, Image.open(io.BytesIO(make_image("PNG"))))
    assert out["c2pa"]["present"] and not out["strong_ai"]
    ai = make_image("PNG") + b"jumb c2pa digitalSourceType trainedAlgorithmicMedia"
    out = metadata.extract(ai, Image.open(io.BytesIO(make_image("PNG"))))
    assert out["strong_ai"]


def test_clean_image_has_no_findings_and_evidence_is_sanitised():
    raw = make_image("JPEG")
    assert metadata.extract(raw, Image.open(io.BytesIO(raw)))["findings"] == []
    raw = _png_with_text(Software="Midjourney\x00\u202e<script>")
    f = metadata.extract(raw, Image.open(io.BytesIO(raw)))["findings"][0]
    assert "\x00" not in f["evidence"] and "\u202e" not in f["evidence"]


def test_camera_exif_is_reported_but_never_lowers_ai_flag():
    im = Image.fromarray(np.zeros((32, 32, 3), np.uint8))
    ex = Image.Exif()
    ex[271], ex[272], ex[305] = "Canon", "EOS R5", "Stable Diffusion"
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=ex)
    out = metadata.extract(buf.getvalue(), Image.open(io.BytesIO(buf.getvalue())))
    assert out["strong_ai"] and any(f["id"] == "camera_exif" for f in out["findings"])


# ---------------------------------------------------------------- frequency features
@pytest.mark.parametrize("size", [(32, 32), (200, 200), (700, 500)])
def test_frequency_features_shape_and_finite(size):
    f = frequency.features(Image.open(io.BytesIO(make_image("PNG", size))))
    assert f.shape == (frequency.N_FEATURES,) and np.isfinite(f).all()


def test_frequency_features_separate_smooth_from_noise():
    noise = Image.fromarray(np.random.default_rng(1).integers(0, 255, (128, 128, 3), dtype=np.uint8))
    smooth = Image.fromarray(np.tile(np.linspace(0, 255, 128, dtype=np.uint8)[:, None, None], (1, 128, 3)))
    assert np.abs(frequency.features(noise) - frequency.features(smooth)).max() > 1.0


# ---------------------------------------------------------------- fusion / decision
CFG = {"members": ["a", "b"], "weights": [1.0, 1.0], "bias": 0.0}


def test_fuse_sums_weighted_logits():
    out = fusion.fuse({"a": 2.0, "b": 2.0}, CFG)
    assert out["p"] == pytest.approx(fusion.sigmoid(4.0)) and out["disagreement"] == pytest.approx(0, abs=1e-9)


def test_decision_bands_and_confidence():
    t = {"real_max": 0.4, "ai_min": 0.6, "disagreement_max": 0.35}
    assert fusion.decide(0.88, 0.0, t, 512, False)["verdict"] == "ai_generated"
    d = fusion.decide(0.07, 0.0, t, 512, False)
    assert d["verdict"] == "real" and d["confidence"] == pytest.approx(0.93)
    d = fusion.decide(0.56, 0.0, t, 512, False)
    assert d["verdict"] == "inconclusive" and d["confidence"] == pytest.approx(0.56)


def test_disagreement_and_tiny_images_widen_the_inconclusive_band():
    t = {"real_max": 0.4, "ai_min": 0.6, "disagreement_max": 0.35}
    assert fusion.decide(0.65, 0.5, t, 512, False)["verdict"] == "inconclusive"
    assert fusion.decide(0.62, 0.0, t, 32, False)["verdict"] == "inconclusive"
    assert fusion.decide(0.62, 0.0, t, 512, False)["verdict"] == "ai_generated"


def test_provenance_only_raises_the_score():
    t = {}
    d = fusion.decide(0.05, 0.0, t, 512, True)
    assert d["verdict"] == "ai_generated" and d["p"] >= 0.98 and d["source"] == "provenance"


# ---------------------------------------------------------------- metrics vs scikit-learn
def test_metrics_match_sklearn():
    from sklearn import metrics as S
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500)
    p = np.clip(y * 0.6 + rng.normal(0.2, 0.25, 500), 0.001, 0.999)
    r = M.binary_report(y, p)
    assert r["roc_auc"] == pytest.approx(S.roc_auc_score(y, p))
    assert r["average_precision"] == pytest.approx(S.average_precision_score(y, p))
    assert r["accuracy"] == pytest.approx(S.accuracy_score(y, p >= .5))
    assert r["recall"] == pytest.approx(S.recall_score(y, p >= .5))
    assert r["precision"] == pytest.approx(S.precision_score(y, p >= .5))
    assert r["f1"] == pytest.approx(S.f1_score(y, p >= .5))
    assert r["mcc"] == pytest.approx(S.matthews_corrcoef(y, p >= .5))
    assert r["mae"] == pytest.approx(S.mean_absolute_error(y, p))
    assert r["mse"] == pytest.approx(S.mean_squared_error(y, p))
    assert r["log_loss"] == pytest.approx(S.log_loss(y, p), rel=1e-6)
    assert r["brier"] == pytest.approx(S.brier_score_loss(y, p))
    json.dumps(M.clean(r))   # must be valid JSON


def test_selective_report():
    y = np.array([0, 0, 1, 1]); p = np.array([0.1, 0.5, 0.5, 0.9])
    s = M.selective_report(y, p, 0.4, 0.6)
    assert s["coverage"] == 0.5 and s["accuracy_decided"] == 1.0
