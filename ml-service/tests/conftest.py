import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
from PIL import Image


def make_image(fmt="PNG", size=(96, 96), seed=0, **save_kw) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 255, (size[1], size[0], 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, fmt, **save_kw)
    return buf.getvalue()


@pytest.fixture
def png_bytes():
    return make_image("PNG")
