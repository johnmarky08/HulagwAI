# HulagwAI ML service

FastAPI service that loads the trained **model bundle** once and answers `POST /v1/analyze`. Only Laravel talks to it.

```bash
python -m venv .venv && .venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
copy .env.example .env        # set ML_SERVICE_TOKEN (same value as the Laravel .env)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001      # or: composer run dev
python -m app.verify          # checks an installed bundle
pytest                        # needs: pip install -r requirements-dev.txt
```

| Endpoint (header `X-Internal-Token` required) | |
|---|---|
| `POST /v1/analyze` | multipart `image` → verdict, probabilities, components, provenance findings, JPEG preview + thumbnail (base64) |
| `GET /v1/model` | bundle name/version/hash, thresholds, evaluation metrics |
| `GET /v1/health` | `{status, model_loaded, metadata_only}` |

`models/current/` must contain `config.json`, `manifest.json`, `metrics.json`, `clip_head.safetensors`, `cnn.safetensors`, `freq_mlp.safetensors` (produced by training stage 8). First start downloads the CLIP backbone (≈ 350 MB for ViT-B-16) from Hugging Face and caches it; afterwards set `HF_HUB_OFFLINE=1` if you want zero network access.

Code map: `app/forensics/` (metadata + frequency) · `app/detectors/` (members, fusion, bundle loader) · `app/pipeline.py` · `app/preprocess.py` (shared with training) · `training/` (Colab pipeline).
