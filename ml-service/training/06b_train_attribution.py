"""Stage 6b - "Which AI family made this image?"  (generator attribution)

A softmax-linear head on the embeddings the detector already computes (CLIP image embedding + fine-tuned ConvNeXt
embedding), so attribution adds no extra model at serving time. Trained on AI images only, with:
  * class-balanced loss and regularisation chosen on VALIDATION (macro-F1)
  * temperature scaling + an abstention threshold `tau` fitted on VALIDATION   -> an honest "unknown"
  * CIFAKE excluded (every image is 32x32, so it would teach "tiny image = Stable Diffusion")
  * the same random degradations as detection training (JPEG/blur/resize) on half of the training images
The test split is evaluated once at the end; unseen generators (Synthbuster) are reported separately.
"""
import random

import numpy as np
import pandas as pd
from safetensors.numpy import save_file

from app.attribution import FAMILIES, FAMILY_IDS
from training import members_eval as ME
from training import metrics as M
from training.augment import degrade
from training.common import done, load_manifest, log, open_rgb, parse, save_json

TARGET_ACC_WHEN_ACCEPTED = 0.80


class _DS:
    def __init__(self, paths, degrade_p, seed):
        self.p, self.dp, self.seed = paths, degrade_p, seed

    def __len__(self): return len(self.p)

    def __getitem__(self, i):
        img = open_rgb(self.p[i])
        if img is not None and self.dp and random.Random(self.seed + i).random() < self.dp:
            img = degrade(img, random.Random(self.seed * 31 + i))
        return i, img


def embed(ctx, paths, members, degrade_p=0.0):
    """[N, Dclip+Dcnn] embeddings (same code path as production); rows of unreadable images are NaN."""
    from torch.utils.data import DataLoader

    X = None
    w = ctx.prof["workers"]                    # full-size images in flight: keep it small (free Colab has ~12 GB RAM)
    dl = DataLoader(_DS(paths, degrade_p, ctx.args.seed), batch_size=2, num_workers=w, collate_fn=list,
                    **({"prefetch_factor": 2} if w else {}))
    for n, batch in enumerate(dl):
        for i, img in batch:
            if img is None:
                continue
            _, fc = members["clip"].analyze(img)
            _, fn = members["cnn"].analyze(img)
            v = np.concatenate([fc, fn]).astype(np.float32)
            if X is None:
                X = np.full((len(paths), v.shape[0]), np.nan, dtype=np.float32)
            X[i] = v
        if n % 800 == 0:
            log.info("embeddings %d/%d", min((n + 1) * 2, len(paths)), len(paths))
    return X


def softmax(z):
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def per_family(y, pred, k):
    cm = np.zeros((k, k), dtype=int)
    for a, b in zip(y, pred):
        cm[a, b] += 1
    prec = np.divide(np.diag(cm), cm.sum(0), out=np.zeros(k), where=cm.sum(0) > 0)
    rec = np.divide(np.diag(cm), cm.sum(1), out=np.zeros(k), where=cm.sum(1) > 0)
    f1 = np.divide(2 * prec * rec, prec + rec, out=np.zeros(k), where=(prec + rec) > 0)
    return cm, prec, rec, f1


def main() -> None:
    import torch

    ctx = parse("Train generator attribution")
    out = ctx.artifacts / "attribution_head.safetensors"
    if done(out, ctx):
        return
    df = load_manifest(ctx)
    if "family" not in df:
        log.warning("manifest has no 'family' column - attribution skipped (re-run stage 1 with --force)")
        return
    fk = df[(df.label == 1) & df["attr_ok"].astype(bool) & df["family"].notna()]
    counts = fk[fk.split == "train"]["family"].value_counts()
    classes = [f for f in FAMILY_IDS if counts.get(f, 0) >= ctx.prof["attr_min"]]
    dropped = {f: int(counts.get(f, 0)) for f in FAMILY_IDS if f not in classes}
    if len(classes) < 2:
        log.warning("fewer than 2 generator families with enough training images (%s) - attribution skipped. "
                    "Enable OpenFake or pass --generator-root.", dict(counts))
        return
    log.info("attribution classes: %s | dropped (too few images): %s", classes, dropped)
    idx = {f: i for i, f in enumerate(classes)}
    fk = fk[fk.family.isin(classes)].reset_index(drop=True)

    members = ME.build_members(ctx)
    emb = {}
    for split, dp in (("train", 0.5), ("val", 0.0), ("test", 0.0)):
        sub = fk[fk.split == split].reset_index(drop=True)
        X = embed(ctx, sub["path"].tolist(), members, dp)
        if X is None:                           # e.g. a dataset that only made it into train - skip, don't fail the run
            log.warning("no readable AI images of families %s in the %s split - attribution skipped "
                        "(detection is unaffected)", classes, split)
            return
        ok = ~np.isnan(X).any(1)
        emb[split] = (X[ok], sub["family"].map(idx).to_numpy()[ok])
    (xtr, ytr), (xva, yva), (xte, yte) = emb["train"], emb["val"], emb["test"]
    K, D = len(classes), xtr.shape[1]
    mean, std = xtr.mean(0), xtr.std(0) + 1e-6
    z = lambda a: torch.tensor((a - mean) / std, dtype=torch.float32)  # noqa: E731
    Xtr, Ytr, Xva = z(xtr), torch.tensor(ytr), z(xva)
    w_cls = torch.tensor(len(ytr) / (K * np.maximum(np.bincount(ytr, minlength=K), 1)), dtype=torch.float32)

    best = (-1.0, None)
    for wd in (1e-4, 1e-3, 1e-2, 1e-1):
        torch.manual_seed(ctx.args.seed)
        lin = torch.nn.Linear(D, K)
        opt = torch.optim.AdamW(lin.parameters(), lr=5e-3, weight_decay=wd)
        for _ in range(ctx.prof["attr_epochs"]):
            loss = torch.nn.functional.cross_entropy(lin(Xtr), Ytr, weight=w_cls)
            opt.zero_grad(); loss.backward(); opt.step()
        with torch.no_grad():
            pv = lin(Xva).argmax(1).numpy()
        _, _, _, f1 = per_family(yva, pv, K)
        macro = float(f1[np.bincount(yva, minlength=K) > 0].mean())
        log.info("weight_decay=%g  val macro-F1=%.4f  acc=%.4f", wd, macro, (pv == yva).mean())
        if macro > best[0]:
            best = (macro, {k: v.detach().clone() for k, v in lin.state_dict().items()})
    W, b = best[1]["weight"].numpy(), best[1]["bias"].numpy()
    Wr, br = W / std, b - (W * (mean / std)).sum(1)            # fold the standardisation into the head
    logits = lambda x: x @ Wr.T + br                              # noqa: E731

    lv = logits(xva)                                              # temperature scaling on validation
    temps = np.linspace(0.5, 4.0, 36)
    nll = [-np.log(np.clip(softmax(lv / t)[np.arange(len(yva)), yva], 1e-9, 1)).mean() for t in temps]
    T = float(temps[int(np.argmin(nll))])
    pv = softmax(lv / T)
    tau = 0.6                                                     # fallback if no threshold reaches the target
    for t in np.arange(0.40, 0.96, 0.01):              # never name a generator below 40% confidence
        acc_m = pv.max(1) >= t
        if acc_m.sum() >= max(10, 0.2 * len(yva)) and (pv.argmax(1)[acc_m] == yva[acc_m]).mean() >= TARGET_ACC_WHEN_ACCEPTED:
            tau = float(round(t, 2)); break
    log.info("temperature=%.2f  tau=%.2f", T, tau)

    save_file({"weight": Wr.astype(np.float32), "bias": br.astype(np.float32)}, str(out))
    save_json(ctx.artifacts / "attribution.json", {"families": classes, "inputs": ["clip", "cnn"], "tau": tau, "temperature": T, "dim": int(D)})

    # ---- held-out test (evaluated once) ----------------------------------------------------------------------------
    pt = softmax(logits(xte) / T)
    pred = pt.argmax(1)
    cm, prec, rec, f1 = per_family(yte, pred, K)
    acc_m = pt.max(1) >= tau
    present = np.bincount(yte, minlength=K) > 0
    rep = {
        "families": classes, "labels": {f: FAMILIES[f] for f in classes}, "dropped_families": dropped,
        "n_train": int(len(ytr)), "n_val": int(len(yva)), "tau": tau, "temperature": T, "val_macro_f1": best[0],
        "test": {
            "n": int(len(yte)), "accuracy": float((pred == yte).mean()),
            "top3_accuracy": float(np.mean([yte[i] in np.argsort(-pt[i])[:3] for i in range(len(yte))])),
            "macro_f1": float(f1[present].mean()), "coverage": float(acc_m.mean()),
            "accuracy_when_accepted": float((pred[acc_m] == yte[acc_m]).mean()) if acc_m.any() else None,
            "ece": M.ece((pred == yte).astype(int), pt.max(1)),
            "per_family": {f: {"n": int(cm[i].sum()), "precision": float(prec[i]), "recall": float(rec[i]), "f1": float(f1[i])} for i, f in enumerate(classes)},
            "confusion": {"labels": classes, "matrix": cm.tolist()},
            "chance_level": float(1 / K),
        },
        "note": ("Closed-set attribution over generator FAMILIES. Images from generators outside this list are answered 'unknown' only "
                 "when the head is not confident - it can still be confidently wrong. CIFAKE is excluded. Measured on a held-out split of "
                 "the same datasets; accuracy on new generators or versions is lower (see 'ood')."),
    }

    ood = ctx.work / "ood_manifest.csv"
    if ood.is_file():
        od = pd.read_csv(ood)
        od = od[od["family"].notna()].reset_index(drop=True) if "family" in od else od.iloc[0:0]
        if len(od):
            Xo = embed(ctx, od["path"].tolist(), members)
            ok = ~np.isnan(Xo).any(1)
            od, Xo = od[ok].reset_index(drop=True), Xo[ok]
            po = softmax(logits(Xo) / T)
            top = po.argmax(1)
            res = {}
            for g, grp in od.groupby("generator"):
                ii = grp.index.to_numpy()
                fam = grp["family"].iloc[0]
                row = {"n": int(len(ii)), "true_family": fam, "in_training": fam in idx,
                       "answered_rate": float((po[ii].max(1) >= tau).mean()),
                       "most_common_prediction": classes[int(np.bincount(top[ii], minlength=K).argmax())]}
                if fam in idx:
                    row["accuracy"] = float((top[ii] == idx[fam]).mean())
                res[str(g)] = row
            rep["ood"] = {"name": "Synthbuster (generators never seen in training)", "per_generator": res}
    save_json(ctx.reports / "attribution_metrics.json", M.clean(rep))
    t = rep["test"]
    log.info("ATTRIBUTION test n=%d acc=%.4f top3=%.4f macroF1=%.4f coverage=%.2f acc@answered=%s (chance %.2f)",
             t["n"], t["accuracy"], t["top3_accuracy"], t["macro_f1"], t["coverage"], t["accuracy_when_accepted"], 1 / K)


if __name__ == "__main__":
    main()
