"""Stage 5 - train the tiny MLP on spectrum / noise-residual features (CPU, minutes)."""
import random
from multiprocessing import Pool

import numpy as np
from safetensors.numpy import save_file

from app.forensics import frequency
from training import metrics as M
from training.augment import degrade
from training.common import cached_rows, done, drop_cache, load_manifest, log, open_rgb, parse, paths_hash


def feat(args):
    path, seed, aug = args
    img = open_rgb(path)
    if img is None:
        return None
    if aug:
        img = degrade(img, random.Random(seed))
    return frequency.features(img)


def extract(ctx, name: str, df, aug: str, procs: int, seed: int):
    """aug = 'all' (training: every image goes through the random degradations, which leave ~20 % untouched) or
    'half' (validation: every other image degraded, so the score reflects both clean and re-compressed inputs).
    Saved chunk by chunk to <work>/cache/freq_<name>/, so a disconnect does not restart the extraction."""
    paths = df["path"].tolist()
    jobs = [(p, seed + i, aug == "all" or (aug == "half" and i % 2 == 1)) for i, p in enumerate(paths)]

    def chunk(s, e):                          # last column: 1 = readable image, 0 = unreadable (row dropped)
        with Pool(procs) as pool:
            res = pool.map(feat, jobs[s:e], chunksize=16)
        a = np.full((e - s, frequency.N_FEATURES + 1), np.nan, dtype=np.float32)
        for i, r in enumerate(res):
            a[i, -1] = r is not None
            if r is not None:
                a[i, :-1] = r
        return a

    key = {"paths": paths_hash(paths), "aug": aug, "seed": seed, "n_features": frequency.N_FEATURES}
    a = cached_rows(ctx, f"freq_{name}", key, len(paths), chunk, chunk=2000)
    keep = np.flatnonzero(a[:, -1] == 1)
    return a[keep, :-1], df["label"].to_numpy()[keep]


def main() -> None:
    import os

    import torch

    ctx = parse("Train frequency MLP")
    out = ctx.artifacts / "freq_mlp.safetensors"
    if done(out, ctx):
        return
    df = load_manifest(ctx)
    cap = ctx.prof["freq_max"]
    tr = df[df.split == "train"].sample(n=min(cap, (df.split == "train").sum()), random_state=ctx.args.seed)
    va = df[df.split == "val"].sample(n=min(cap // 5 + 1, (df.split == "val").sum()), random_state=ctx.args.seed)
    procs = max(1, (os.cpu_count() or 2) - 0)
    log.info("extracting frequency features: %d train / %d val (%d procs)", len(tr), len(va), procs)
    xtr, ytr = extract(ctx, "train", tr, "all", procs, ctx.args.seed)
    xva, yva = extract(ctx, "val", va, "half", procs, ctx.args.seed + 1)
    np.savez(ctx.features / "freq_feats.npz", xtr=xtr, ytr=ytr, xva=xva, yva=yva)   # reused by the scikit-learn baselines
    mean, std = xtr.mean(0), xtr.std(0) + 1e-6
    f = lambda a: torch.tensor((a - mean) / std, dtype=torch.float32)  # noqa: E731

    torch.manual_seed(ctx.args.seed)
    net = torch.nn.Sequential(torch.nn.Linear(frequency.N_FEATURES, 64), torch.nn.ReLU(), torch.nn.Dropout(0.1), torch.nn.Linear(64, 1))
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-3)
    X, Y, Xv = f(xtr), torch.tensor(ytr, dtype=torch.float32), f(xva)
    best = (-1.0, None)
    for ep in range(60):
        net.train()
        perm = torch.randperm(len(X))
        for i in range(0, len(X), 256):
            b = perm[i:i + 256]
            loss = torch.nn.functional.binary_cross_entropy_with_logits(net(X[b]).squeeze(1), Y[b])
            opt.zero_grad(); loss.backward(); opt.step()
        net.eval()
        with torch.no_grad():
            auc = M.roc_auc(yva, torch.sigmoid(net(Xv).squeeze(1)).numpy())
        if auc > best[0]:
            best = (auc, {k: v.detach().clone() for k, v in net.state_dict().items()})
    sd = best[1]
    save_file({"w1": sd["0.weight"].numpy().T.copy(), "b1": sd["0.bias"].numpy(), "w2": sd["3.weight"].numpy().T.copy(), "b2": sd["3.bias"].numpy(),
               "mean": mean.astype(np.float32), "std": std.astype(np.float32)}, str(out))
    drop_cache(ctx, "freq_train", "freq_val")   # freq_feats.npz keeps the features for stage 7
    log.info("saved %s (val AUC %.4f)", out.name, best[0])


if __name__ == "__main__":
    main()
