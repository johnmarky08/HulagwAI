"""Run the REAL inference members (app.detectors.members) over a manifest -> logits. Same code path as production."""
from __future__ import annotations

import numpy as np

from app.detectors.members import MEMBERS
from training.common import Ctx, log, open_rgb

ORDER = ["clip", "cnn", "frequency"]


def build_members(ctx: Ctx) -> dict:
    cfgs = {"clip": ctx.clip_cfg, "cnn": ctx.cnn_cfg, "frequency": {}}
    return {n: MEMBERS[n](cfgs[n], ctx.artifacts, device=ctx.device) for n in ORDER}


class _DS:
    def __init__(self, paths): self.p = paths
    def __len__(self): return len(self.p)
    def __getitem__(self, i): return i, open_rgb(self.p[i])


def compute_logits(ctx: Ctx, paths: list[str], members: dict, transform=None) -> np.ndarray:
    """-> [N, 3] logits in ORDER; rows of unreadable images are NaN."""
    from torch.utils.data import DataLoader

    out = np.full((len(paths), len(ORDER)), np.nan, dtype=np.float64)
    dl = DataLoader(_DS(paths), batch_size=16, num_workers=ctx.prof["workers"], collate_fn=list)
    for n, batch in enumerate(dl):
        for i, img in batch:
            if img is None:
                continue
            if transform is not None:
                img = transform(img, i)
            for j, name in enumerate(ORDER):
                out[i, j] = members[name].logit(img)
        if n % 100 == 0:
            log.info("logits %d/%d", min((n + 1) * 16, len(paths)), len(paths))
    return out
