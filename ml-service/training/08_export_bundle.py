"""Stage 8 - assemble the model bundle (config + weights + metrics + SHA-256 manifest) and zip it for download."""
import hashlib
import json
import shutil
from datetime import datetime, timezone

import numpy as np
from PIL import Image

from app.detectors.bundle import Bundle
from training import model_card
from training.common import log, parse, run_info, save_json


def main() -> None:
    ctx = parse("Export model bundle")
    f = json.loads((ctx.artifacts / "fusion.json").read_text())
    name = f"hulagwai-ensemble-{ctx.args.version}"
    root = ctx.work / "bundle" / name
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)

    for fn in ("clip_head.safetensors", "cnn.safetensors", "freq_mlp.safetensors", "attribution_head.safetensors"):
        if (ctx.artifacts / fn).is_file():
            shutil.copy(ctx.artifacts / fn, root / fn)
    attr_cfg = json.loads((ctx.artifacts / "attribution.json").read_text()) if (ctx.artifacts / "attribution.json").is_file() else None
    if (ctx.reports / "metrics.json").is_file():
        shutil.copy(ctx.reports / "metrics.json", root / "metrics.json")
    else:
        log.warning("metrics.json missing - run training.07_evaluate first, otherwise the PDF report shows 'not evaluated'")
    # provenance: everything an instructor needs to audit/reproduce the run (not loaded by the service)
    prov = root / "provenance"
    prov.mkdir()
    for src in (ctx.manifest, ctx.work / "datasets.json", ctx.reports / "leakage_check.json", ctx.reports / "cv_clip.json"):
        if src.is_file():
            shutil.copy(src, prov / src.name)
    save_json(prov / "run_info.json", run_info(ctx))
    if (ctx.reports / "metrics.json").is_file():
        (prov / "MODEL_CARD.md").write_text(model_card.build(ctx), encoding="utf-8")
    datasets = json.loads((ctx.work / "datasets.json").read_text()) if (ctx.work / "datasets.json").is_file() else []
    save_json(root / "config.json", {
        "name": "hulagwai-ensemble", "version": ctx.args.version, "trained_at": datetime.now(timezone.utc).isoformat(), "profile": ctx.profile_name,
        "clip": ctx.clip_cfg, "cnn": ctx.cnn_cfg, "frequency": {}, **({"attribution": attr_cfg} if attr_cfg else {}), "fusion": f["fusion"], "thresholds": f["thresholds"], "trained_on": datasets})
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir()) if p.is_file() and p.name != "manifest.json"}
    save_json(root / "manifest.json", {"files": files})

    # smoke-load exactly like the API will, to catch a broken bundle before you download it
    b = Bundle(root)
    img = Image.fromarray(np.random.default_rng(0).integers(0, 255, (256, 256, 3), dtype=np.uint8))
    log.info("bundle loads OK, sample logits: %s", b.logits(img))
    zip_path = shutil.make_archive(str(ctx.work / name), "zip", root)
    log.info("DONE -> %s\nDownload it and unzip into ml-service/models/current/ on your laptop.", zip_path)


if __name__ == "__main__":
    main()
