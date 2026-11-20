"""Stage 3b - 5-fold stratified cross-validation of the CLIP-feature classifier (scikit-learn).

Purpose: show that the validation score is not a lucky split (mean +- std over folds). The cached train features
are used; the VALIDATION and TEST splits are never touched here, so no information leaks into the final evaluation.
"""
import numpy as np

from training.common import done, log, parse, save_json


def main() -> None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    from sklearn.model_selection import StratifiedKFold

    ctx = parse("Cross-validation")
    out = ctx.reports / "cv_clip.json"
    if done(out, ctx):
        return
    d = np.load(ctx.features / "train_clean.npz")
    x, y = d["x"].astype(np.float32), d["y"]
    if len(x) > 30_000:                                   # keep it quick
        idx = np.random.default_rng(ctx.args.seed).choice(len(x), 30_000, replace=False)
        x, y = x[idx], y[idx]
    res = {"accuracy": [], "f1": [], "roc_auc": []}
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=ctx.args.seed).split(x, y):
        clf = LogisticRegression(C=1.0, max_iter=1000).fit(x[tr], y[tr])
        p = clf.predict_proba(x[te])[:, 1]
        res["accuracy"].append(accuracy_score(y[te], p >= .5)); res["f1"].append(f1_score(y[te], p >= .5)); res["roc_auc"].append(roc_auc_score(y[te], p))
    summary = {"folds": 5, "n": int(len(x)), **{k: {"mean": float(np.mean(v)), "std": float(np.std(v)), "per_fold": [float(a) for a in v]} for k, v in res.items()}}
    save_json(out, summary)
    log.info("5-fold CV  acc %.4f +- %.4f   AUC %.4f +- %.4f", summary["accuracy"]["mean"], summary["accuracy"]["std"], summary["roc_auc"]["mean"], summary["roc_auc"]["std"])


if __name__ == "__main__":
    main()
