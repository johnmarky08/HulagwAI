"""End-to-end bundle test using only the numpy-based frequency member (no torch needed)."""
import hashlib
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient
from safetensors.numpy import save_file

from app.detectors.bundle import Bundle, BundleError
from app.forensics import frequency
from tests.conftest import make_image

TOKEN = "z" * 40


def build_bundle(root):
    rng = np.random.default_rng(0)
    d = frequency.N_FEATURES
    save_file({"w1": rng.normal(size=(d, 8)).astype(np.float32), "b1": np.zeros(8, np.float32),
               "w2": rng.normal(size=(8, 1)).astype(np.float32), "b2": np.zeros(1, np.float32),
               "mean": np.zeros(d, np.float32), "std": np.ones(d, np.float32)}, str(root / "freq_mlp.safetensors"))
    (root / "config.json").write_text(json.dumps({
        "name": "test-ensemble", "version": "9.9.9", "frequency": {},
        "fusion": {"members": ["frequency"], "weights": [1.0], "bias": 0.0},
        "thresholds": {"real_max": 0.4, "ai_min": 0.6, "disagreement_max": 0.35}}))
    (root / "metrics.json").write_text(json.dumps({"generated_at": "2026-11-01T00:00:00Z", "test": {"n": 10, "accuracy": 0.9}}))
    files = {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in ("config.json", "freq_mlp.safetensors", "metrics.json")}
    (root / "manifest.json").write_text(json.dumps({"files": files}))


def test_bundle_loads_predicts_and_detects_tampering(tmp_path):
    build_bundle(tmp_path)
    b = Bundle(tmp_path)
    assert b.version == "9.9.9" and len(b.weights_sha256) == 64
    assert b.info()["metrics"]["test"]["accuracy"] == 0.9
    (tmp_path / "freq_mlp.safetensors").write_bytes((tmp_path / "freq_mlp.safetensors").read_bytes() + b"x")
    with pytest.raises(BundleError):
        Bundle(tmp_path)


def test_api_with_bundle(monkeypatch, tmp_path):
    build_bundle(tmp_path)
    monkeypatch.setenv("ML_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("ML_ALLOW_METADATA_ONLY", "false")
    monkeypatch.setenv("ML_MODEL_DIR", str(tmp_path))
    from app.main import app
    h = {"X-Internal-Token": TOKEN}
    with TestClient(app) as c:
        r = c.post("/v1/analyze", files={"image": ("a.jpg", make_image("JPEG", (300, 300)), "image/jpeg")}, headers=h)
        assert r.status_code == 200, r.text
        j = r.json()
        assert 0 <= j["ai_probability"] <= 1 and j["model"]["version"] == "9.9.9"
        assert set(j["components"]) == {"frequency"} and j["verdict"] in {"real", "ai_generated", "inconclusive"}
        assert c.get("/v1/model", headers=h).json()["evaluated_at"] == "2026-11-01T00:00:00Z"
