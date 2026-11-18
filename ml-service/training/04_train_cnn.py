"""Stage 4 - fine-tune a ConvNeXt end-to-end on native-resolution crops (needs a GPU; ~25 min/epoch on a Colab T4 for ~200k images)."""
import random

import numpy as np
from safetensors.torch import save_file

from app import preprocess as P
from training import metrics as M
from training.augment import degrade, random_native_crop
from training.common import done, load_manifest, log, open_rgb, parse


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
    dl_tr = DataLoader(DS(tr, True, ctx.args.seed), batch_size=bs, shuffle=True, num_workers=w, drop_last=True, pin_memory=dev == "cuda")
    dl_va = DataLoader(DS(va, False, ctx.args.seed), batch_size=bs * 2, num_workers=w)

    net = timm.create_model(ctx.cnn_cfg["arch"], pretrained=ctx.prof["pretrained"], num_classes=1).to(dev)
    epochs = ctx.prof["cnn_epochs"]
    opt = torch.optim.AdamW(net.parameters(), lr=1e-4, weight_decay=0.05)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-4, total_steps=max(1, epochs * len(dl_tr)), pct_start=0.1)
    scaler = torch.amp.GradScaler(enabled=dev == "cuda")
    best = -1.0
    for ep in range(epochs):
        net.train()
        for step, (x, y) in enumerate(dl_tr):
            m = y >= 0
            if not m.any():
                continue
            x, y = x[m].to(dev), y[m].to(dev)
            with torch.autocast(dev, enabled=dev == "cuda"):
                loss = torch.nn.functional.binary_cross_entropy_with_logits(net(x).squeeze(1).float(), y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
            if step % 200 == 0:
                log.info("epoch %d step %d/%d loss %.4f", ep + 1, step, len(dl_tr), loss.item())
        auc, acc = evaluate(net, dl_va, dev)
        log.info("epoch %d  val AUC %.4f  acc %.4f", ep + 1, auc, acc)
        if auc >= best:                       # keep the best epoch only
            best = auc
            save_file({k: v.detach().cpu().contiguous() for k, v in net.state_dict().items()}, str(out))
    log.info("saved %s (best val AUC %.4f)", out.name, best)


if __name__ == "__main__":
    main()
