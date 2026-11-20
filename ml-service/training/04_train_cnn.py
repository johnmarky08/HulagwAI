"""Stage 4 - fine-tune a ConvNeXt end-to-end on native-resolution crops (needs a GPU; ~25 min/epoch on a Colab T4 for ~200k images).

Resumable: a checkpoint is saved to --work (Drive) every 10 minutes and after each epoch; re-running the same command
after a disconnect continues from it."""
import random
import time

import numpy as np
from safetensors.torch import save_file

from app import preprocess as P
from training import metrics as M
from training.augment import degrade, random_native_crop
from training.common import atomic_replace, done, load_manifest, log, open_rgb, parse, paths_hash

CKPT_EVERY_S = 600          # mid-epoch checkpoint to Drive every 10 min (an epoch can be longer than a Colab session)


class DS:
    def __init__(self, df, train: bool, seed: int):
        self.p, self.y, self.train, self.seed = df["path"].tolist(), df["label"].tolist(), train, seed
        self.rng = random.Random(seed)

    def __len__(self): return len(self.p)

    def __getitem__(self, i):
        import torch
        img = open_rgb(self.p[i])
        if img is None:
            return torch.zeros(3, P.CROP, P.CROP), -1.0
        if self.train:
            r = random.Random(self.seed * 7919 + i + random.randint(0, 10**6))
            img = random_native_crop(degrade(img, r), r)
        else:
            img = P.native_crops(img, P.CROP, 1)[0]
        arr = P.crops_to_array([img], P.IMAGENET_MEAN, P.IMAGENET_STD)[0]
        return torch.from_numpy(arr), float(self.y[i])


def evaluate(net, dl, dev):
    import torch
    ps, ys = [], []
    net.eval()
    with torch.inference_mode(), torch.autocast(dev, enabled=dev == "cuda"):
        for x, y in dl:
            ps.append(torch.sigmoid(net(x.to(dev)).float().squeeze(1)).cpu().numpy()); ys.append(y.numpy())
    p, y = np.concatenate(ps), np.concatenate(ys)
    m = y >= 0
    return M.roc_auc(y[m].astype(int), p[m]), float(((p[m] >= .5) == y[m]).mean())


def main() -> None:
    import timm
    import torch
    from torch.utils.data import DataLoader

    ctx = parse("Fine-tune CNN")
    out = ctx.artifacts / "cnn.safetensors"
    if done(out, ctx):
        return
    dev = ctx.device
    df = load_manifest(ctx)
    tr, va = df[df.split == "train"], df[df.split == "val"]
    bs, w = ctx.prof["cnn_batch"], ctx.prof["workers"]
    ds_tr = DS(tr, True, ctx.args.seed)
    dl_va = DataLoader(DS(va, False, ctx.args.seed), batch_size=bs * 2, num_workers=w)
    steps_per_epoch = len(ds_tr) // bs                    # drop_last=True

    net = timm.create_model(ctx.cnn_cfg["arch"], pretrained=ctx.prof["pretrained"], num_classes=1).to(dev)
    epochs = ctx.prof["cnn_epochs"]
    opt = torch.optim.AdamW(net.parameters(), lr=1e-4, weight_decay=0.05)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-4, total_steps=max(1, epochs * steps_per_epoch), pct_start=0.1)
    scaler = torch.amp.GradScaler(enabled=dev == "cuda")

    # ---- resumable checkpoint on Drive -----------------------------------------------------------------------------
    # cnn_ckpt.pt (model + optimizer + LR schedule + position) is written every CKPT_EVERY_S seconds and after every
    # epoch; the best epoch's weights go to cnn_best.safetensors. cnn.safetensors - the file that marks this stage as
    # done - is only written when ALL epochs are finished, so a disconnect never leaves a half-trained CNN behind.
    ckpt, best_f = ctx.artifacts / "cnn_ckpt.pt", ctx.artifacts / "cnn_best.safetensors"
    sig = {"n_train": len(ds_tr), "n_val": len(va), "bs": bs, "epochs": epochs, "arch": ctx.cnn_cfg["arch"], "seed": ctx.args.seed,
           "manifest": paths_hash(tr["path"].tolist())}
    start_ep, start_step, best = 0, 0, -1.0
    if ckpt.is_file() and not ctx.args.force:
        try:
            c = torch.load(ckpt, map_location=dev, weights_only=False)
            if c.get("sig") == sig and (c["best"] < 0 or best_f.is_file()):
                net.load_state_dict(c["model"]); opt.load_state_dict(c["opt"])
                sched.load_state_dict(c["sched"]); scaler.load_state_dict(c["scaler"])
                start_ep, start_step, best = c["epoch"], c["step"], c["best"]
                log.info("resuming CNN training from checkpoint: epoch %d, step %d/%d (best val AUC so far %.4f)",
                         start_ep + 1, start_step, steps_per_epoch, best)
            else:
                log.warning("cnn_ckpt.pt is from a different setup (data/batch/epochs changed) - starting over")
        except Exception as e:  # noqa: BLE001 - a corrupt checkpoint must not kill the run
            log.warning("could not read cnn_ckpt.pt (%s: %s) - starting over", type(e).__name__, e)

    def save_ckpt(epoch: int, step: int) -> None:
        tmp = ckpt.with_name(ckpt.name + ".tmp")
        torch.save({"sig": sig, "epoch": epoch, "step": step, "best": best, "model": net.state_dict(),
                    "opt": opt.state_dict(), "sched": sched.state_dict(), "scaler": scaler.state_dict()}, tmp)
        atomic_replace(tmp, ckpt)

    last = time.monotonic()
    for ep in range(start_ep, epochs):
        # the shuffle order of an epoch is fixed by (seed, epoch), so a resumed epoch continues with the same images
        perm = torch.randperm(len(ds_tr), generator=torch.Generator().manual_seed(ctx.args.seed * 1000 + ep)).tolist()
        first = start_step if ep == start_ep else 0
        dl_tr = DataLoader(ds_tr, batch_size=bs, sampler=perm[first * bs: steps_per_epoch * bs], num_workers=w,
                           drop_last=True, pin_memory=dev == "cuda")
        net.train()
        for step, (x, y) in enumerate(dl_tr, start=first):
            m = y >= 0
            if m.any():
                x, y = x[m].to(dev), y[m].to(dev)
                with torch.autocast(dev, enabled=dev == "cuda"):
                    loss = torch.nn.functional.binary_cross_entropy_with_logits(net(x).squeeze(1).float(), y)
                opt.zero_grad(set_to_none=True)
                scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
                if step % 200 == 0:
                    log.info("epoch %d step %d/%d loss %.4f", ep + 1, step, steps_per_epoch, loss.item())
            if time.monotonic() - last >= CKPT_EVERY_S:
                save_ckpt(ep, step + 1)
                last = time.monotonic()
                log.info("checkpoint saved (epoch %d, step %d/%d)", ep + 1, step + 1, steps_per_epoch)
        auc, acc = evaluate(net, dl_va, dev)
        log.info("epoch %d  val AUC %.4f  acc %.4f", ep + 1, auc, acc)
        if auc >= best:                       # keep the best epoch only
            best = auc
            tmp = best_f.with_name(best_f.name + ".tmp")
            save_file({k: v.detach().cpu().contiguous() for k, v in net.state_dict().items()}, str(tmp))
            atomic_replace(tmp, best_f)
        save_ckpt(ep + 1, 0)
        last = time.monotonic()
    if not best_f.is_file():                 # val AUC was never a number (e.g. NaN) - keep the final weights
        log.warning("no epoch had a valid val AUC - saving the last epoch's weights")
        save_file({k: v.detach().cpu().contiguous() for k, v in net.state_dict().items()}, str(best_f))
    atomic_replace(best_f, out)              # training finished -> this stage is now done
    ckpt.unlink(missing_ok=True)
    log.info("saved %s (best val AUC %.4f)", out.name, best)


if __name__ == "__main__":
    main()
