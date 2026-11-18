"""Stage 7 - honest evaluation on the held-out TEST split (+ robustness + unseen generators) -> metrics.json.

This file feeds the PDF report (accuracy, precision, recall, F1, ROC-AUC, MAE, MSE, Brier, log-loss, ECE ...).
"""
import io
import json
import random
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from PIL import ImageFilter

from app.detectors import fusion
from training import members_eval as ME
from training import metrics as M
from training.common import done, load_manifest, log, parse, save_json


def fuse_all(z: np.ndarray, cfg: dict) -> np.ndarray:
    w, b = np.asarray(cfg["weights"]), cfg["bias"]
    return 1 / (1 + np.exp(-np.clip(b + z @ w, -30, 30)))


def jpeg(q):
    def f(img, _i):
        buf = io.BytesIO(); img.save(buf, "JPEG", quality=q); buf.seek(0)
        from PIL import Image
        return Image.open(buf).convert("RGB")
    return f


TRANSFORMS = {
    "jpeg_q75": jpeg(75), "jpeg_q50": jpeg(50),
    "downscale_0.5": lambda im, _i: im.resize((max(16, im.width // 2), max(16, im.height // 2))),
    "blur_1.0": lambda im, _i: im.filter(ImageFilter.GaussianBlur(1.0)),
}


def main() -> None:
    ctx = parse("Evaluate")
    out = ctx.reports / "metrics.json"
    if done(out, ctx):
        return
    fcfg = json.loads((ctx.artifacts / "fusion.json").read_text())
    df = load_manifest(ctx)
    te = df[df.split == "test"].reset_index(drop=True)
    members = ME.build_members(ctx)

    z = ME.compute_logits(ctx, te["path"].tolist(), members)
    ok = ~np.isnan(z).any(1)
    te, z = te[ok].reset_index(drop=True), z[ok]
    y, p = te["label"].to_numpy(), fuse_all(z, fcfg["fusion"])
    th = fcfg["thresholds"]

    report: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "profile": ctx.profile_name, "test": M.binary_report(y, p, 0.5)}
    report["selective"] = M.selective_report(y, p, th["real_max"], th["ai_min"])
    report["components"] = {n: {"roc_auc": M.roc_auc(y, 1 / (1 + np.exp(-z[:, j]))),
                                "accuracy": float(((z[:, j] >= 0) == y).mean())} for j, n in enumerate(ME.ORDER)}
    report["per_source"] = {s: {k: M.binary_report(y[m], p[m])[k] for k in ("n", "accuracy", "recall", "specificity", "roc_auc")}
                            for s in te["source"].unique() for m in [(te["source"] == s).to_numpy()]}
    fake = te["label"] == 1
    report["per_generator"] = {}
    for (src, gen), grp in te[fake].groupby(["source", "generator"]):
        idx = grp.index.to_numpy()
        report["per_generator"][f"{src}/{gen}"] = {"n": int(len(idx)), "recall": float((p[idx] >= 0.5).mean())}

    # robustness on a fixed random subset (same images for every transformation)
    n = min(ctx.prof["robustness_n"], len(te))
    sub = te.sample(n=n, random_state=ctx.args.seed).index.to_numpy()
    rob = {"none": {"accuracy": float(((p[sub] >= .5) == y[sub]).mean()), "n": int(n)}}
    for name, tf in TRANSFORMS.items():
        zz = ME.compute_logits(ctx, te.loc[sub, "path"].tolist(), members, transform=tf)
        good = ~np.isnan(zz).any(1)
        rob[name] = {"accuracy": float(((fuse_all(zz[good], fcfg["fusion"]) >= .5) == y[sub][good]).mean()), "n": int(good.sum())}
    report["robustness"] = rob

    ood_path = ctx.work / "ood_manifest.csv"
    if ood_path.is_file():
        od = pd.read_csv(ood_path)
        zo = ME.compute_logits(ctx, od["path"].tolist(), members)
        g = ~np.isnan(zo).any(1)
        od, po = od[g].reset_index(drop=True), fuse_all(zo[g], fcfg["fusion"])
        fk, rl = (od.label == 1).to_numpy(), (od.label == 0).to_numpy()
        report["ood"] = {"name": "Synthbuster (generators never seen in training)", "n_fake": int(fk.sum()), "recall": float((po[fk] >= .5).mean()) if fk.any() else None,
                         "n_real": int(rl.sum()) if rl.any() else None, "specificity": float((po[rl] < .5).mean()) if rl.any() else None,
                         "per_generator": {gname: float((po[(od.generator == gname).to_numpy() & fk] >= .5).mean()) for gname in od[fk].generator.unique()}}
    datasets = ctx.work / "datasets.json"
    report["datasets"] = json.loads(datasets.read_text()) if datasets.is_file() else []
    report["thresholds"], report["fusion"] = th, fcfg["fusion"]
    save_json(out, M.clean(report))
    t = report["test"]
    log.info("TEST n=%d acc=%.4f prec=%.4f recall=%.4f f1=%.4f auc=%.4f MAE=%.4f", t["n"], t["accuracy"], t["precision"], t["recall"], t["f1"], t["roc_auc"], t["mae"])


if __name__ == "__main__":
    main()
