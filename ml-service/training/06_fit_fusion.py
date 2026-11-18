"""Stage 6 - learn how to combine the three members (logistic regression on VALIDATION logits) and pick the
Real / Inconclusive / AI thresholds. The test split is never touched here."""
import numpy as np

from app.detectors import fusion
from training import members_eval as ME
from training import metrics as M
from training.common import done, load_manifest, log, parse, save_json


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
    z = ME.compute_logits(ctx, va["path"].tolist(), members)
    ok = ~np.isnan(z).any(1)
    z, y = z[ok], va["label"].to_numpy()[ok]
    np.savez(ctx.reports / "val_logits.npz", z=z, y=y)

    for j, name in enumerate(ME.ORDER):
        log.info("member %-9s val AUC %.4f", name, M.roc_auc(y, 1 / (1 + np.exp(-z[:, j]))))
    lr = LogisticRegression(C=1.0, max_iter=2000).fit(z, y)
    cfg = {"members": ME.ORDER, "weights": [float(w) for w in lr.coef_[0]], "bias": float(lr.intercept_[0])}
    p = np.array([fusion.sigmoid(cfg["bias"] + sum(w * v for w, v in zip(cfg["weights"], row))) for row in z])
    th = pick_thresholds(y, p)
    log.info("fusion %s | val AUC %.4f | thresholds %s", cfg, M.roc_auc(y, p), th)
    save_json(out, {"fusion": cfg, "thresholds": {**{k: th[k] for k in ("real_max", "ai_min")}, "disagreement_max": 0.35},
                    "val_auc": M.roc_auc(y, p), "val_coverage": th["coverage"]})


if __name__ == "__main__":
    main()
