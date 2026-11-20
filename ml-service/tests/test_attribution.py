import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from safetensors.numpy import save_file

from app import attribution as A
from app.forensics import evidence, metadata

TOKEN = "q" * 40


@pytest.mark.parametrize("name,fam", [
    ("sd-1.5", "stable_diffusion"), ("stable_diffusion_v_1_4", "stable_diffusion"), ("imagenet_ai_0419_sdv4", "stable_diffusion"),
    ("sdxl-turbo", "sdxl_sd3"), ("sd-3.5", "sdxl_sd3"), ("flux-1.1-pro", "flux"), ("midjourney-6", "midjourney"),
    ("imagenet_midjourney", "midjourney"), ("dall-e-3", "dalle"), ("DALLE2", "dalle"), ("gpt-image-1.5", "gpt_image"),
    ("nano-banana-pro", "google"), ("imagen-4", "google"), ("biggan", "gan"), ("stylegan2", "gan"), ("ProjectedGAN", "gan"),
    ("ideogram-3.0", "other_ai"), ("glide", "other_ai"), ("organ", "other_ai"),
    ("laion", None), ("imagenet", None), ("nature", None), ("real", None), ("", None), (None, None),
])
def test_family_mapping(name, fam):
    assert A.family_of(name) == fam


def _png(**chunks):
    info = PngInfo()
    for k, v in chunks.items():
        info.add_text(k, v)
    buf = io.BytesIO()
    Image.fromarray(np.zeros((40, 40, 3), np.uint8)).save(buf, "PNG", pnginfo=info)
    return buf.getvalue()


def test_metadata_reports_the_declared_generator():
    raw = _png(parameters="cat\nSteps: 20, Sampler: Euler a, CFG scale: 7, Seed: 1, Model: sdxl_base_1.0")
    f = next(x for x in metadata.extract(raw, Image.open(io.BytesIO(raw)))["findings"] if x["id"] == "sd_webui_parameters")
    assert f["generator"] == "sdxl_base_1.0" and A.family_of(f["generator"]) == "sdxl_sd3"
    raw = _png(Software="Midjourney")
    f = metadata.extract(raw, Image.open(io.BytesIO(raw)))["findings"][0]
    assert A.family_of(f["generator"]) == "midjourney"


def _head(tmp_path, families, w, b, tau=0.6):
    save_file({"weight": np.asarray(w, np.float32), "bias": np.asarray(b, np.float32)}, str(tmp_path / "attribution_head.safetensors"))
    return A.AttributionHead({"families": families, "inputs": ["clip", "cnn"], "tau": tau, "temperature": 1.0}, tmp_path)


def test_attribution_head_names_family_or_abstains(tmp_path):
    h = _head(tmp_path, ["flux", "midjourney"], [[5, 0, 0, 0], [0, 5, 0, 0]], [0, 0])
    out = h.predict({"clip": np.array([1.0, 0.0]), "cnn": np.array([0.0, 0.0])})
    assert out["decision"] == "family" and out["top"][0]["family"] == "flux" and out["top"][0]["label"] == "FLUX"
    out = h.predict({"clip": np.array([0.05, 0.05]), "cnn": np.array([0.0, 0.0])})   # ~50/50 -> below tau
    assert out["decision"] == "unknown"
    assert h.predict({"clip": None, "cnn": np.zeros(2)})["available"] is False
    assert h.predict({"clip": np.zeros(3), "cnn": np.zeros(2)})["reason"] == "feature_size_mismatch"


def test_attribution_head_rejects_mismatched_family_list(tmp_path):
    with pytest.raises(ValueError):
        _head(tmp_path, ["flux"], [[1, 0, 0, 0], [0, 1, 0, 0]], [0, 0])


class _FakeCnn:
    """Scores a crop by its mean brightness -> the bright quadrant must become the hot region."""
    def patch_logits(self, crops):
        return np.array([(np.asarray(c, np.float32).mean() / 255 - 0.5) * 12 for c in crops])


def test_patch_map_heatmap_and_regions():
    arr = np.zeros((500, 500, 3), np.uint8)
    arr[:224, 276:] = 255                                   # upper-right is "suspicious"
    img = Image.fromarray(arr)
    pm = evidence.patch_map(img, _FakeCnn())
    assert (pm["rows"], pm["cols"]) == (2, 2)
    ev = evidence.build({"cnn": {"p": 0.9}}, {"findings": []}, [], 0.1, pm, 0.9)
    assert ev["heatmap"]["available"] and ev["regions"][0]["where"] == "upper-right"
    assert any(f["id"] == "hot_region" for f in ev["flags"])
    jpg = Image.open(io.BytesIO(__import__("base64").b64decode(evidence.overlay_jpeg_b64(img, pm))))
    assert jpg.format == "JPEG" and max(jpg.size) <= 480 and not jpg.getexif()
    assert evidence.patch_map(Image.new("RGB", (100, 100)), _FakeCnn()) is None      # smaller than a patch
    assert evidence.patch_map(Image.new("RGB", (300, 256)), _FakeCnn()) is None      # one patch -> no location info
    pm = evidence.patch_map(Image.new("RGB", (460, 230)), _FakeCnn())
    assert (pm["rows"], pm["cols"]) == (1, 2)
    ev = evidence.build({"cnn": {"p": 0.9}}, {"findings": []}, [], 0.1, {**pm, "scores": np.array([[0.9, 0.2]])}, 0.9)
    assert ev["regions"][0]["where"] == "left"


def test_evidence_says_nothing_ai_for_real_images_and_lists_warnings():
    ev = evidence.build({"cnn": {"p": 0.1}, "clip": {"p": 0.2}}, {"findings": []}, ["heavily_compressed"], 0.05, None, 0.15)
    assert [f["category"] for f in ev["flags"]] == ["Limitations"]
    assert ev["regions"] == [] and ev["heatmap"]["available"] is False
    assert "not proof" in ev["note"]


def test_evidence_flags_mixed_signals():
    ev = evidence.build({"cnn": {"p": 0.92}, "clip": {"p": 0.2}, "frequency": {"p": 0.7}}, {"findings": []}, [], 0.3, None, 0.75)
    ids = [f["id"] for f in ev["flags"]]
    assert "signal_cnn" in ids and "signal_frequency" in ids and "mixed_signals" in ids


def test_api_returns_metadata_attribution_without_a_model(monkeypatch, tmp_path):
    monkeypatch.setenv("ML_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("ML_ALLOW_METADATA_ONLY", "true")
    monkeypatch.setenv("ML_MODEL_DIR", str(tmp_path / "none"))
    from app.main import app
    raw = _png(parameters="a dog\nSteps: 30, Sampler: DPM++, CFG scale: 6, Seed: 9, Model: flux1-dev")
    with TestClient(app) as c:
        j = c.post("/v1/analyze", files={"image": ("a.png", raw, "image/png")}, headers={"X-Internal-Token": TOKEN}).json()
    assert j["verdict"] == "ai_generated"
    assert j["attribution"]["source"] == "metadata" and j["attribution"]["top"][0]["family"] == "flux"
    assert j["evidence"]["flags"][0]["category"] == "Provenance" and j["heatmap_jpeg_b64"] is None
    with TestClient(app) as c:
        j = c.post("/v1/analyze", files={"image": ("b.png", _png(), "image/png")}, headers={"X-Internal-Token": TOKEN}).json()
    assert j["attribution"] == {"available": False, "reason": "attribution_model_not_installed"}  # no model, no metadata -> no guess
