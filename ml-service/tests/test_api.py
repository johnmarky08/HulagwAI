import base64
import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from tests.conftest import make_image

TOKEN = "x" * 40


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("ML_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("ML_ALLOW_METADATA_ONLY", "true")
    monkeypatch.setenv("ML_MODEL_DIR", str(tmp_path / "nothing"))
    from app.main import app
    with TestClient(app) as c:
        yield c


H = {"X-Internal-Token": TOKEN}


def post(c, data, headers=H, name="a.png"):
    return c.post("/v1/analyze", files={"image": (name, data, "application/octet-stream")}, headers=headers)


def test_rejects_missing_or_wrong_token(client, png_bytes):
    assert post(client, png_bytes, headers={}).status_code == 401
    assert post(client, png_bytes, headers={"X-Internal-Token": "y" * 40}).status_code == 401
    assert client.get("/v1/health").status_code == 401


def test_no_docs_endpoints(client):
    for p in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(p).status_code == 404


def test_metadata_only_mode_returns_inconclusive_with_valid_previews(client, png_bytes):
    r = post(client, png_bytes)
    assert r.status_code == 200
    j = r.json()
    assert j["verdict"] == "inconclusive" and j["ai_probability"] == 0.5 and "no_ml_model" in j["warnings"]
    assert j["model"]["name"] == "metadata-only"
    for k in ("preview_jpeg_b64", "thumb_jpeg_b64"):
        im = Image.open(io.BytesIO(base64.b64decode(j[k])))
        assert im.format == "JPEG" and not im.getexif()


def test_declared_ai_provenance_is_caught_even_without_a_model(client):
    raw = make_image("PNG") + b"jumb c2pa trainedAlgorithmicMedia"
    j = post(client, raw).json()
    assert j["verdict"] == "ai_generated" and j["decision"]["source"] == "provenance"


def test_garbage_and_wrong_formats_are_422(client):
    assert post(client, b"<?php system($_GET[0]); ?>").status_code == 422
    buf = io.BytesIO(); Image.new("RGB", (40, 40)).save(buf, "GIF")
    assert post(client, buf.getvalue()).status_code == 422
    assert post(client, b"").status_code in (413, 422)


def test_oversize_is_413(client):
    assert post(client, b"0" * (6 * 1024 * 1024 + 10)).status_code == 413


def test_503_when_model_missing_and_fallback_disabled(monkeypatch, tmp_path, png_bytes):
    monkeypatch.setenv("ML_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("ML_ALLOW_METADATA_ONLY", "false")
    monkeypatch.setenv("ML_MODEL_DIR", str(tmp_path / "nothing"))
    from app.main import app
    with TestClient(app) as c:
        assert post(c, png_bytes).status_code == 503
        assert c.get("/v1/model", headers=H).status_code == 503


def test_service_refuses_to_start_without_token(monkeypatch):
    monkeypatch.setenv("ML_SERVICE_TOKEN", "short")
    monkeypatch.delenv("ML_ALLOW_INSECURE_DEV", raising=False)
    from app.main import app
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass
