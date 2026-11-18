"""HulagwAI ML service - FastAPI. Bind to 127.0.0.1 only; Laravel is the only intended client.

    uvicorn app.main:app --host 127.0.0.1 --port 8001
"""
from __future__ import annotations

import asyncio
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app import config, pipeline
from app.detectors.bundle import Bundle, BundleError

log = logging.getLogger("hulagwai.ml")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = config.load_settings()
    if (len(s.token) < 32) and not s.allow_insecure_dev:
        raise RuntimeError("ML_SERVICE_TOKEN must be set (>= 32 chars) and match the Laravel .env value.")
    app.state.settings = s
    app.state.sem = asyncio.Semaphore(s.concurrency)
    app.state.bundle, app.state.bundle_error = None, None
    try:
        import torch  # noqa: WPS433  (optional until a bundle is installed)
        torch.set_num_threads(s.torch_threads)
    except Exception:  # pragma: no cover
        pass
    try:
        app.state.bundle = Bundle(s.model_dir)
        log.info("model bundle loaded: %s %s", app.state.bundle.name, app.state.bundle.version)
    except BundleError as e:
        app.state.bundle_error = str(e)
        log.warning("no usable model bundle: %s", e)
    except Exception as e:  # missing torch/timm, corrupt weights ...
        app.state.bundle_error = f"{type(e).__name__}: {e}"
        log.error("model bundle failed to load: %s", app.state.bundle_error)
    yield


# No /docs, /redoc or /openapi.json: nothing to enumerate for an attacker.
app = FastAPI(title="HulagwAI ML", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


def require_token(request: Request, x_internal_token: str | None = Header(default=None)) -> None:
    s: config.Settings = request.app.state.settings
    if s.allow_insecure_dev and not s.token:
        return
    if not x_internal_token or not hmac.compare_digest(x_internal_token.encode(), s.token.encode()):
        raise HTTPException(status_code=401, detail="unauthorized")


@app.middleware("http")
async def no_store(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.get("/v1/health", dependencies=[Depends(require_token)])
async def health(request: Request):
    st = request.app.state
    return {"status": "ok", "model_loaded": st.bundle is not None, "metadata_only": st.bundle is None and st.settings.allow_metadata_only}


@app.get("/v1/model", dependencies=[Depends(require_token)])
async def model_info(request: Request):
    b: Bundle | None = request.app.state.bundle
    if b is None:
        raise HTTPException(status_code=503, detail="model_not_ready")
    return b.info()


@app.post("/v1/analyze", dependencies=[Depends(require_token)])
async def analyze(request: Request, image: UploadFile = File(...)):
    st = request.app.state
    limit = st.settings.max_upload_bytes
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit + 65536:
        raise HTTPException(status_code=413, detail="too_large")
    data = await image.read(limit + 1)
    if not data or len(data) > limit:
        raise HTTPException(status_code=413 if data else 422, detail="too_large" if data else "empty")

    try:
        async with st.sem:
            result = await run_in_threadpool(pipeline.analyze, data, st.settings, st.bundle)
    except pipeline.ModelNotReady:
        raise HTTPException(status_code=503, detail="model_not_ready")
    except pipeline.ImageError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        log.exception("analysis crashed")            # stack goes to the server log, never to the client
        return JSONResponse({"detail": "analysis_failed"}, status_code=500)
    return result
