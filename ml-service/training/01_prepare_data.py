"""Stage 1 - download datasets and build manifest.csv (+ ood_manifest.csv for unseen generators)."""
import random

import pandas as pd

from training import data_sources as D
from training.common import done, log, parse, save_json


def main() -> None:
    ctx = parse("Build the training manifest")
    if done(ctx.manifest, ctx):
        return
    rng = random.Random(ctx.args.seed)
    rows = D.prepare_cifake(ctx, rng) + D.prepare_artifact(ctx, rng) + D.prepare_genimage(ctx, rng)
    df = D.balance(pd.DataFrame(rows), ctx.args.seed)
    df.to_csv(ctx.manifest, index=False)
    log.info("manifest: %d images\n%s", len(df), df.groupby(["source", "split", "label"]).size().unstack().to_string())

    used = set(df["source"].unique())
    info = [d for d in D.DATASETS_INFO if d["name"] in used]
    if ctx.args.with_ood:
        ood = D.prepare_synthbuster(ctx)
        if ood is not None:
            ood.to_csv(ctx.work / "ood_manifest.csv", index=False)
            info.append(next(d for d in D.DATASETS_INFO if d["name"] == "Synthbuster"))
            log.info("OOD set: %d images", len(ood))
    counts = df.groupby("source")["split"].value_counts().unstack(fill_value=0)
    for d in info:
        if d["name"] in counts.index:
            d.update({f"n_{s}": int(counts.loc[d["name"]].get(s, 0)) for s in ("train", "val", "test")})
    save_json(ctx.work / "datasets.json", info)


if __name__ == "__main__":
    main()
