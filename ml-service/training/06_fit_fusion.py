"""Stage 6 - learn how to combine the three members (logistic regression on VALIDATION logits) and pick the
Real / Inconclusive / AI thresholds. The test split is never touched here."""
import random

import numpy as np

from app.detectors import fusion
from training import members_eval as ME
from training.augment import degrade
from training import metrics as M
from training.common import done, drop_cache, load_manifest, log, parse, save_json


def pick_thresholds(y, p, target=0.97):
    """Widest 'decided' region such that precision of AI calls and of Real calls stay >= target on validation."""
    best = {"real_max": 0.40, "ai_min": 0.60, "coverage": 0.0}
    for ai_min in np.arange(0.50, 0.99, 0.01):
        sel = p >= ai_min
        if sel.sum() >= 20 and (y[sel] == 1).mean() >= target:
            best["ai_min"] = float(round(ai_min, 2)); break
    for real_max in np.arange(0.50, 0.01, -0.01):
        sel = p <= real_max
        if sel.sum() >= 20 and (y[sel] == 0).mean() >= target:
            best["real_max"] = float(round(real_max, 2)); break
    best["real_max"] = min(best["real_max"], best["ai_min"] - 0.02)
    best["coverage"] = float(((p <= best["real_max"]) | (p >= best["ai_min"])).mean())
    return best


def main() -> None:
    from sklearn.linear_model import LogisticRegression

    ctx = parse("Fit fusion")
    out = ctx.artifacts / "fusion.json"
    if done(out, ctx):
        return
    df = load_manifest(ctx)
    va = df[df.split == "val"].reset_index(drop=True)
    members = ME.build_members(ctx)
    paths, labels, srcs = va["path"].tolist(), va["label"].to_numpy(), va["source"].to_numpy()
    # Two views of every validation image: as stored, and re-compressed/resized like a typical upload. Fitting the
    # fusion on both stops it from trusting a member that only works on pristine files.
    seed = ctx.args.seed + 17
    z_clean = ME.compute_logits(ctx, paths, members, cache="val_clean")
    z_deg = ME.compute_logits(ctx, paths, members, transform=lambda img, i: degrade(img, random.Random(seed + i)),
                              cache="val_degraded")
    z, y, src = np.vstack([z_clean, z_deg]), np.concatenate([labels, labels]), np.concatenate([srcs, srcs])
    ok = ~np.isnan(z).any(1)
    z, y, src = z[ok], y[ok], src[ok]
    if len(np.unique(y)) < 2:
        raise SystemExit("validation split has only one class - cannot fit the fusion")
    np.savez(ctx.reports / "val_logits.npz", z=z, y=y)

    # every dataset counts equally (otherwise the largest one - e.g. CIFAKE - decides the weights and thresholds)
    _, inv, cnt = np.unique(src, return_inverse=True, return_counts=True)
    sw = (len(src) / (len(cnt) * cnt))[inv]
    for j, name in enumerate(ME.ORDER):
        log.info("member %-9s val AUC %.4f", name, M.roc_auc(y, 1 / (1 + np.exp(-z[:, j]))))
    lr = LogisticRegression(C=1.0, max_iter=2000).fit(z, y, sample_weight=sw)
    cfg = {"members": ME.ORDER, "weights": [float(w) for w in lr.coef_[0]], "bias": float(lr.intercept_[0])}
    p = np.array([fusion.sigmoid(cfg["bias"] + sum(w * v for w, v in zip(cfg["weights"], row))) for row in z])
    th = pick_thresholds(y, p)
    log.info("fusion %s | val AUC %.4f (clean+degraded, %d sources) | thresholds %s", cfg, M.roc_auc(y, p), len(cnt), th)
    save_json(out, {"fusion": cfg, "thresholds": {**{k: th[k] for k in ("real_max", "ai_min")}, "disagreement_max": 0.35},
                    "val_auc": M.roc_auc(y, p), "val_coverage": th["coverage"]})
    drop_cache(ctx, "logits_val_clean", "logits_val_degraded")   # val_logits.npz keeps them for stage 7


if __name__ == "__main__":
    main()
