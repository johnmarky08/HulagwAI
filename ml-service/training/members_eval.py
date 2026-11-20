"""Run the REAL inference members (app.detectors.members) over a manifest -> logits. Same code path as production."""
from __future__ import annotations

import numpy as np

from app.detectors.members import MEMBERS
from training.common import Ctx, artifacts_fingerprint, cached_rows, log, open_rgb, paths_hash

ORDER = ["clip", "cnn", "frequency"]


def build_members(ctx: Ctx) -> dict:
    cfgs = {"clip": ctx.clip_cfg, "cnn": ctx.cnn_cfg, "frequency": {}}
    return {n: MEMBERS[n](cfgs[n], ctx.artifacts, device=ctx.device) for n in ORDER}


class _DS:
    """Rows start..end of `paths`; yields the GLOBAL index so transforms seeded by it give the same result per chunk."""
    def __init__(self, paths, start=0): self.p, self.start = paths, start
    def __len__(self): return len(self.p)
    def __getitem__(self, i): return self.start + i, open_rgb(self.p[i])


def _logits_range(ctx: Ctx, paths: list[str], members: dict, transform, start: int, end: int) -> np.ndarray:
    from torch.utils.data import DataLoader

    out = np.full((end - start, len(ORDER)), np.nan, dtype=np.float64)
    # full-size decoded images travel between processes here: keep only ~10 in flight (a 24 MP photo is ~70 MB)
    w = ctx.prof["workers"]
    dl = DataLoader(_DS(paths[start:end], start), batch_size=2, num_workers=w, collate_fn=list,
                    **({"prefetch_factor": 2} if w else {}))
    for n, batch in enumerate(dl):
        for i, img in batch:
            if img is None:
                continue
            if transform is not None:
                img = transform(img, i)
            for j, name in enumerate(ORDER):
                out[i - start, j] = members[name].logit(img)
        if n % 800 == 0:
            log.info("logits %d/%d", min(start + (n + 1) * 2, len(paths)), len(paths))
    return out


def compute_logits(ctx: Ctx, paths: list[str], members: dict, transform=None, cache: str | None = None) -> np.ndarray:
    """-> [N, 3] logits in ORDER; rows of unreadable images are NaN.

    cache: a name unique to this (paths, transform) pair, e.g. 'val_degraded'. The logits are then saved chunk by
    chunk under <work>/cache/logits_<cache>/ and a re-run after a disconnect continues where it stopped. The cache is
    keyed on the paths and the trained member weights, so a retrained model never reuses old logits."""
    if not paths:
        return np.full((0, len(ORDER)), np.nan)
    if cache is None:
        return _logits_range(ctx, paths, members, transform, 0, len(paths))
    key = {"paths": paths_hash(paths), "models": artifacts_fingerprint(ctx), "seed": ctx.args.seed}
    return cached_rows(ctx, f"logits_{cache}", key, len(paths),
                       lambda s, e: _logits_range(ctx, paths, members, transform, s, e), chunk=500)
