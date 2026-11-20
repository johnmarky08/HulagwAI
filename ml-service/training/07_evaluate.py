"""Stage 7 - honest evaluation on the held-out TEST split -> reports/metrics.json (read by the PDF report and the web app).

Contents: headline metrics, confusion matrix, ROC + calibration data, model comparison (baselines vs. final),
5-fold CV, per-dataset / per-generator results, error analysis, robustness, and unseen-generator (OOD) results.
Model selection and thresholds were fixed on the VALIDATION split (stage 6); the test split is only measured here.
"""
import io
import json
import os
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageFilter

from app.forensics import frequency
from training import members_eval as ME
from training import metrics as M
from training.common import done, load_manifest, log, open_rgb, parse, save_json


def fuse_all(z: np.ndarray, cfg: dict) -> np.ndarray:
    w, b = np.asarray(cfg["weights"]), cfg["bias"]
    return 1 / (1 + np.exp(-np.clip(b + z @ w, -30, 30)))


def sig(x): return 1 / (1 + np.exp(-np.clip(x, -30, 30)))


def jpeg(q):
    def f(img, _i):
        buf = io.BytesIO(); img.save(buf, "JPEG", quality=q); buf.seek(0)
        return Image.open(buf).convert("RGB")
    return f


TRANSFORMS = {
    "jpeg_q75": jpeg(75), "jpeg_q50": jpeg(50),
    "downscale_0.5": lambda im, _i: im.resize((max(16, im.width // 2), max(16, im.height // 2))),
    "blur_1.0": lambda im, _i: im.filter(ImageFilter.GaussianBlur(1.0)),
}


def _feat(path):
    img = open_rgb(path)
    return None if img is None else frequency.features(img)


def classic_baselines(ctx, te_paths, y_te, keep_mask):
    """scikit-learn baselines on the SAME hand-crafted features (no deep learning) -> {name: (val_auc, p_test)}."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    f = np.load(ctx.features / "freq_feats.npz")
    with Pool(max(1, os.cpu_count() or 1)) as pool:
        feats = pool.map(_feat, te_paths, chunksize=64)
    ok = np.array([x is not None for x in feats])
    xte = np.stack([x for x in feats if x is not None])
    models = {
        "Logistic Regression on hand-crafted features (scikit-learn)": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
        "Random Forest on hand-crafted features (scikit-learn)": RandomForestClassifier(n_estimators=200, max_depth=14, n_jobs=-1, random_state=ctx.args.seed),
    }
    out = {}
    for name, clf in models.items():
        clf.fit(f["xtr"], f["ytr"])
        val_auc = M.roc_auc(f["yva"], clf.predict_proba(f["xva"])[:, 1])
        p = np.full(len(te_paths), np.nan)
        p[ok] = clf.predict_proba(xte)[:, 1]
        out[name] = (val_auc, p)
    return out


def row(name, family, y, p, val_auc, note=""):
    m = ~np.isnan(p)
    r = M.binary_report(y[m], p[m])
    return {"name": name, "family": family, "note": note, "val_roc_auc": val_auc,
            **{k: r[k] for k in ("accuracy", "precision", "recall", "f1", "roc_auc")}}


def main() -> None:
    ctx = parse("Evaluate")
    out = ctx.reports / "metrics.json"
    if done(out, ctx):
        return
    fcfg = json.loads((ctx.artifacts / "fusion.json").read_text())
    df = load_manifest(ctx)
    te = df[df.split == "test"].reset_index(drop=True)
    tr_prior = float((df[df.split == "train"].label == 1).mean())
    members = ME.build_members(ctx)

    z = ME.compute_logits(ctx, te["path"].tolist(), members)
    ok = ~np.isnan(z).any(1)
    te, z = te[ok].reset_index(drop=True), z[ok]
    y, p = te["label"].to_numpy(), fuse_all(z, fcfg["fusion"])
    th = fcfg["thresholds"]

    rep: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "profile": ctx.profile_name, "test": M.binary_report(y, p, 0.5)}
    rep["roc"] = M.roc_curve(y, p)
    rep["calibration"] = M.calibration_bins(y, p)
    rep["selective"] = M.selective_report(y, p, th["real_max"], th["ai_min"])
    cv = ctx.reports / "cv_clip.json"
    if cv.is_file():
        rep["cross_validation"] = {"model": "CLIP-feature classifier, 5-fold stratified CV on the training split", **json.loads(cv.read_text())}

    # ---- model comparison (baselines vs alternatives vs final) ------------------------------------------------
    vz = np.load(ctx.reports / "val_logits.npz")
    val_auc_member = {n: M.roc_auc(vz["y"], sig(vz["z"][:, j])) for j, n in enumerate(ME.ORDER)}
    val_auc_fused = M.roc_auc(vz["y"], fuse_all(vz["z"], fcfg["fusion"]))
    cmp_rows = [row("Majority-class baseline", "baseline", y, np.full(len(y), tr_prior), 0.5, "always predicts the most frequent training class")]
    for name, (vauc, pp) in classic_baselines(ctx, te["path"].tolist(), y, ok).items():
        cmp_rows.append(row(name, "baseline", y, pp, vauc, "classical ML, no deep features"))
    labels = {"clip": "CLIP ViT features + linear head", "cnn": "ConvNeXt fine-tuned (CNN)", "frequency": "Frequency/noise MLP"}
    for j, n in enumerate(ME.ORDER):
        cmp_rows.append(row(labels[n] + " (single member)", "alternative", y, sig(z[:, j]), val_auc_member[n]))
    cmp_rows.append(row("HulagwAI ensemble (final model)", "final", y, p, val_auc_fused, "weighted fusion of the three members"))
    best = max(cmp_rows, key=lambda r: r["val_roc_auc"] or 0)
    rep["comparison"] = {
        "rows": cmp_rows, "selected": "HulagwAI ensemble (final model)", "best_on_validation": best["name"],
        "basis": ("Candidates were ranked by ROC-AUC on the VALIDATION split (never on test). "
                  + ("The ensemble had the highest validation ROC-AUC. " if best["family"] == "final" else
                     f"'{best['name']}' scored highest on validation; the ensemble was still kept because it combines independent signals and gives a disagreement estimate used for the 'Inconclusive' verdict - see the limitations. ")
                  + "Test results above are reported once, after the choice was made."),
    }
    rep["components"] = {n: {"roc_auc": M.roc_auc(y, sig(z[:, j])), "accuracy": float(((z[:, j] >= 0) == y).mean())} for j, n in enumerate(ME.ORDER)}

    # ---- breakdowns ---------------------------------------------------------------------------------------------
    rep["per_source"] = {s: {k: M.binary_report(y[m], p[m])[k] for k in ("n", "accuracy", "recall", "specificity", "roc_auc")}
                         for s in te["source"].unique() for m in [(te["source"] == s).to_numpy()]}
    fake = te["label"] == 1
    rep["per_generator"] = {}
    for (src, gen), grp in te[fake].groupby(["source", "generator"]):
        idx = grp.index.to_numpy()
        rep["per_generator"][f"{src}/{gen}"] = {"n": int(len(idx)), "recall": float((p[idx] >= 0.5).mean())}

    # ---- error analysis -----------------------------------------------------------------------------------------
    side = np.array([min(Image.open(pth).size) for pth in te["path"]])
    bucket = np.where(side < 64, "<64 px", np.where(side < 224, "64-223 px", ">=224 px"))
    pred = p >= 0.5
    rep["errors"] = {
        "by_resolution": {b: {"n": int((bucket == b).sum()), "accuracy": float((pred[bucket == b] == y[bucket == b]).mean())} for b in np.unique(bucket)},
        "false_positives_by_source": {k: int(v) for k, v in te[(~fake.to_numpy()) & pred].groupby("source").size().items()},
        "false_negatives_by_generator": {f"{a}/{b}": int(n) for (a, b), n in te[fake.to_numpy() & ~pred].groupby(["source", "generator"]).size().items()},
        "most_confident_mistakes": [
            {"file": Path(te.path[i]).name, "source": te.source[i], "generator": te.generator[i], "label": int(y[i]), "p_ai": round(float(p[i]), 4)}
            for i in np.argsort(-np.abs(p - y))[: 12] if pred[i] != bool(y[i])],
        "note": "Most errors are expected on very small, heavily compressed or edited images and on generators absent from training.",
    }

    # ---- robustness (same fixed subset for each transformation) -------------------------------------------------
    n = min(ctx.prof["robustness_n"], len(te))
    sub = te.sample(n=n, random_state=ctx.args.seed).index.to_numpy()
    rob = {"none": {"accuracy": float(((p[sub] >= .5) == y[sub]).mean()), "n": int(n)}}
    for name, tf in TRANSFORMS.items():
        zz = ME.compute_logits(ctx, te.loc[sub, "path"].tolist(), members, transform=tf)
        good = ~np.isnan(zz).any(1)
        rob[name] = {"accuracy": float(((fuse_all(zz[good], fcfg["fusion"]) >= .5) == y[sub][good]).mean()), "n": int(good.sum())}
    rep["robustness"] = rob

    # ---- unseen generators ----------------------------------------------------------------------------------------
    ood_path = ctx.work / "ood_manifest.csv"
    if ood_path.is_file():
        od = pd.read_csv(ood_path)
        zo = ME.compute_logits(ctx, od["path"].tolist(), members)
        g = ~np.isnan(zo).any(1)
        od, po = od[g].reset_index(drop=True), fuse_all(zo[g], fcfg["fusion"])
        fk, rl = (od.label == 1).to_numpy(), (od.label == 0).to_numpy()
        rep["ood"] = {"name": "Synthbuster (generators never seen in training)", "n_fake": int(fk.sum()), "recall": float((po[fk] >= .5).mean()) if fk.any() else None,
                      "n_real": int(rl.sum()) if rl.any() else None, "specificity": float((po[rl] < .5).mean()) if rl.any() else None,
                      "per_generator": {gn: float((po[(od.generator == gn).to_numpy() & fk] >= .5).mean()) for gn in od[fk].generator.unique()}}

    am = ctx.reports / "attribution_metrics.json"
    if am.is_file():
        rep["attribution"] = json.loads(am.read_text())
    ds, leak = ctx.work / "datasets.json", ctx.reports / "leakage_check.json"
    rep["datasets"] = json.loads(ds.read_text()) if ds.is_file() else []
    rep["leakage_check"] = json.loads(leak.read_text()) if leak.is_file() else None
    rep["thresholds"], rep["fusion"] = th, fcfg["fusion"]
    save_json(out, M.clean(rep))
    t = rep["test"]
    log.info("TEST n=%d acc=%.4f prec=%.4f recall=%.4f f1=%.4f auc=%.4f MAE=%.4f", t["n"], t["accuracy"], t["precision"], t["recall"], t["f1"], t["roc_auc"], t["mae"])
    for r in cmp_rows:
        log.info("  %-62s test acc %.4f  AUC %.4f  (val AUC %.4f)", r["name"], r["accuracy"], r["roc_auc"], r["val_roc_auc"] or 0)


if __name__ == "__main__":
    main()
