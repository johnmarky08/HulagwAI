"""Sanity-check an installed model bundle on your laptop:  python -m app.verify"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from app.config import load_settings
from app.detectors.bundle import Bundle


def main() -> None:
    s = load_settings()
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else s.model_dir
    b = Bundle(root)
    print(f"OK  {b.name} v{b.version}  weights {b.weights_sha256[:16]}...")
    print("thresholds:", b.thresholds)
    print("evaluated:", (b.metrics or {}).get("generated_at", "no metrics.json"))
    img = Image.fromarray(np.random.default_rng(0).integers(0, 255, (300, 300, 3), dtype=np.uint8))
    print("sample logits:", b.logits(img))


if __name__ == "__main__":
    main()
