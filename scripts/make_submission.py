#!/usr/bin/env python3
"""Build the CSST 102 submission ZIP: complete project, trained model included, nothing private or temporary.

    python scripts/make_submission.py [output.zip]
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {".git", "vendor", "node_modules", "__pycache__", ".pytest_cache", ".phpunit.cache", ".venv", "venv", "work", ".idea", ".vscode"}
EXCLUDE_PREFIX = ("storage/logs", "storage/framework", "storage/app/private", "storage/app/public", "bootstrap/cache", "public/build", "database/database.sqlite")
EXCLUDE_NAMES = {".env", "ml-service/.env", ".phpunit.result.cache", "hot", ".DS_Store", "Thumbs.db"}
EXCLUDE_SUFFIX = (".pyc", ".log", ".sqlite", ".sqlite3", ".zip", ".rar", ".key", ".pem")
REQUIRED_MODEL = ["config.json", "manifest.json", "metrics.json", "clip_head.safetensors", "cnn.safetensors", "freq_mlp.safetensors"]


def keep(rel: str, p: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in p.relative_to(ROOT).parts[:-1]):
        return False
    if rel in EXCLUDE_NAMES or p.name in EXCLUDE_NAMES or rel.startswith(EXCLUDE_PREFIX):
        return False
    return not rel.endswith(EXCLUDE_SUFFIX) or rel.startswith("ml-service/models/current/")


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "HulagwAI-submission.zip"
    missing = [f for f in REQUIRED_MODEL if not (ROOT / "ml-service/models/current" / f).is_file()]
    if missing:
        sys.exit("The trained model bundle is missing in ml-service/models/current/: " + ", ".join(missing) +
                 "\nTrain it first (README section 2) - the guideline requires the trained model file in the ZIP.")
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob("*")):
            if p.is_file() and p.resolve() != out.resolve():
                rel = p.relative_to(ROOT).as_posix()
                if keep(rel, p):
                    z.write(p, "HulagwAI/" + rel); n += 1
    print(f"{n} files -> {out}\nNo .env, vendor/, node_modules/, logs or caches included. Re-install with `composer install` + `npm install`.")
    print("Before sending: open the ZIP and check that no secrets slipped in (search for 'ML_SERVICE_TOKEN=' and 'APP_KEY=').")


if __name__ == "__main__":
    main()
