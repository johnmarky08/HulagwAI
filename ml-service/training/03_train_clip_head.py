"""Stage 3 - train the linear (logistic-regression) head on the cached CLIP features. Few minutes, even on CPU."""
import numpy as np
from safetensors.numpy import save_file

from training import metrics as M
from training.common import done, log, parse


def load(ctx, split, views):
    xs, ys = [], []
    for v in views:
        d = np.load(ctx.features / f"{split}_{v}.npz")
        xs.append(d["x"].astype(np.float32)); ys.append(d["y"])
    return np.concatenate(xs), np.concatenate(ys)


def main() -> None:
    import torch

    ctx = parse("Train CLIP linear head")
    out = ctx.artifacts / "clip_head.safetensors"
    if done(out, ctx):
        return
    xtr, ytr = load(ctx, "train", ("clean", "degraded"))
    xva, yva = load(ctx, "val", ("clean", "degraded"))
    dev = ctx.device
    Xtr, Ytr = torch.tensor(xtr, device=dev), torch.tensor(ytr, dtype=torch.float32, device=dev)
    Xva = torch.tensor(xva, device=dev)

    best = (-1.0, None, None)
    for wd in (1e-5, 1e-4, 1e-3, 1e-2):                       # pick the regularisation on the validation set
        torch.manual_seed(ctx.args.seed)
        lin = torch.nn.Linear(Xtr.shape[1], 1).to(dev)
        opt = torch.optim.AdamW(lin.parameters(), lr=2e-3, weight_decay=wd)
        for ep in range(ctx.prof["clip_epochs"]):
            perm = torch.randperm(len(Xtr), device=dev)
            for i in range(0, len(Xtr), 4096):
                b = perm[i:i + 4096]
                loss = torch.nn.functional.binary_cross_entropy_with_logits(lin(Xtr[b]).squeeze(1) * 10, Ytr[b])
                opt.zero_grad(); loss.backward(); opt.step()
        with torch.no_grad():
            pv = torch.sigmoid(lin(Xva).squeeze(1) * 10).cpu().numpy()
        auc = M.roc_auc(yva, pv)
        log.info("weight_decay=%g  val AUC=%.4f  acc=%.4f", wd, auc, ((pv >= .5) == yva).mean())
        if auc > best[0]:
            best = (auc, lin.weight.detach().cpu().numpy() * 10, lin.bias.detach().cpu().numpy() * 10)
    save_file({"weight": best[1].astype(np.float32), "bias": best[2].astype(np.float32)}, str(out))   # x10 folded in
    log.info("saved %s (val AUC %.4f)", out.name, best[0])


if __name__ == "__main__":
    main()
