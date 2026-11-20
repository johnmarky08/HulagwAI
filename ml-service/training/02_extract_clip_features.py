"""Stage 2 - run the FROZEN CLIP image encoder once over the data and cache the features.

Train rows get two views (clean + randomly degraded) so the linear head also learns from compressed/blurred images.
"""
import random

import numpy as np

from app import preprocess as P
from training.augment import degrade, random_native_crop
from training.common import done, load_manifest, log, open_rgb, parse


class DS:
    def __init__(self, df, degraded: bool, seed: int):
        self.paths, self.degraded, self.seed = df["path"].tolist(), degraded, seed

    def __len__(self): return len(self.paths)

    def __getitem__(self, i):
        import torch
        img = open_rgb(self.paths[i])
        if img is None:
            return torch.zeros(3, P.CROP, P.CROP), False
        if self.degraded:                      # degraded view: random native crop (not always the centre) + JPEG/blur/resize
            r = random.Random(self.seed + i)
            crop = random_native_crop(degrade(img, r), r)
        else:
            crop = P.native_crops(img, P.CROP, 1)[0]
        arr = P.crops_to_array([crop], P.CLIP_MEAN, P.CLIP_STD)[0]
        return torch.from_numpy(arr), True


def main() -> None:
    import open_clip
    import torch
    from torch.utils.data import DataLoader

    ctx = parse("Extract frozen CLIP features")
    df = load_manifest(ctx)
    model, _, _ = open_clip.create_model_and_transforms(ctx.clip_cfg["arch"], pretrained=ctx.clip_cfg["pretrained"])
    model = model.eval().to(ctx.device)

    for split, views in (("train", ("clean", "degraded")), ("val", ("clean", "degraded")), ("test", ("clean",))):
        sub = df[df["split"] == split].reset_index(drop=True)
        for view in views:
            out = ctx.features / f"{split}_{view}.npz"
            if done(out, ctx):
                continue
            dl = DataLoader(DS(sub, view == "degraded", ctx.args.seed), batch_size=128, num_workers=ctx.prof["workers"])
            feats, ok = [], []
            with torch.inference_mode(), torch.autocast(ctx.device, enabled=ctx.device == "cuda"):
                for x, valid in dl:
                    f = model.encode_image(x.to(ctx.device)).float()
                    feats.append((f / f.norm(dim=-1, keepdim=True)).cpu().numpy().astype(np.float16)); ok.append(valid.numpy())
                    if len(feats) % 50 == 0:
                        log.info("%s/%s %d/%d", split, view, sum(len(a) for a in feats), len(sub))
            ok = np.concatenate(ok)
            np.savez(out, x=np.concatenate(feats)[ok], y=sub["label"].to_numpy()[ok], idx=np.flatnonzero(ok))
            log.info("saved %s (%d)", out.name, int(ok.sum()))


if __name__ == "__main__":
    main()
