"""Settings read from environment / ml-service/.env (no extra dependency)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.split(" #")[0].strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    token: str
    model_dir: Path
    allow_metadata_only: bool
    max_upload_bytes: int = 6 * 1024 * 1024      # Laravel already caps at 5 MB; this is the second wall
    max_pixels: int = 40_000_000
    max_side: int = 8192
    concurrency: int = 1
    torch_threads: int = 4
    allow_insecure_dev: bool = False


def load_settings() -> Settings:
    model_dir = Path(os.environ.get("ML_MODEL_DIR", "models/current"))
    if not model_dir.is_absolute():
        model_dir = BASE_DIR / model_dir
    return Settings(
        token=os.environ.get("ML_SERVICE_TOKEN", ""),
        model_dir=model_dir,
        allow_metadata_only=_bool("ML_ALLOW_METADATA_ONLY", False),
        concurrency=max(1, int(os.environ.get("ML_MAX_CONCURRENCY", "1"))),
        torch_threads=max(1, int(os.environ.get("ML_TORCH_THREADS", "4"))),
        allow_insecure_dev=_bool("ML_ALLOW_INSECURE_DEV", False),
    )
