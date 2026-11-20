"""Stage 2 - run the FROZEN CLIP image encoder once over the data and cache the features.

Train rows get two views (clean + randomly degraded) so the linear head also learns from compressed/blurred images.
"""
import random

import numpy as np

from app import preprocess as P
from training.augment import degrade, random_native_crop
from training.common import atomic_replace, cached_rows, done, drop_cache, load_manifest, log, open_rgb, parse, paths_hash


class DS:
    """Rows start.. of the split; `i` below is the GLOBAL row index, so chunked extraction gives identical crops."""
    def __init__(self, paths, degraded: bool, seed: int, start: int = 0):
        self.paths, self.degraded, self.seed, self.start = paths, degraded, seed, start

    def __len__(self): return len(self.paths)

    def __getitem__(self, j):
        import torch
        i = self.start + j
        img = open_rgb(self.paths[j])
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
        paths = sub["path"].tolist()
        for view in views:
            out = ctx.features / f"{split}_{view}.npz"
            if done(out, ctx):
                continue

            def chunk(s, e, view=view, split=split, paths=paths):
                """[e-s, D+1] float16 features; last column 1 = readable image. Saved per chunk (resumable)."""
                dl = DataLoader(DS(paths[s:e], view == "degraded", ctx.args.seed, s), batch_size=128,
                                num_workers=ctx.prof["workers"])
                feats, ok = [], []
                with torch.inference_mode(), torch.autocast(ctx.device, enabled=ctx.device == "cuda"):
                    for x, valid in dl:
                        f = model.encode_image(x.to(ctx.device)).float()
                        feats.append((f / f.norm(dim=-1, keepdim=True)).cpu().numpy().astype(np.float16))
                        ok.append(valid.numpy())
                log.info("%s/%s %d/%d", split, view, e, len(paths))
                return np.concatenate([np.concatenate(feats), np.concatenate(ok)[:, None].astype(np.float16)], axis=1)

            key = {"paths": paths_hash(paths), "view": view, "seed": ctx.args.seed, "clip": ctx.clip_cfg}
            a = cached_rows(ctx, f"clip_{split}_{view}", key, len(paths), chunk, chunk=4096)
            ok = a[:, -1] == 1
            tmp = out.with_name(out.stem + ".tmp.npz")
            np.savez(tmp, x=a[ok, :-1], y=sub["label"].to_numpy()[ok], idx=np.flatnonzero(ok))
            atomic_replace(tmp, out)              # a half-written .npz would otherwise be "done" on the next run
            drop_cache(ctx, f"clip_{split}_{view}")   # the .npz is now the saved result
            log.info("saved %s (%d)", out.name, int(ok.sum()))


if __name__ == "__main__":
    main()
