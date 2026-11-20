"""Stage 1 - download datasets and build manifest.csv (+ ood_manifest.csv for unseen generators)."""
import random
from pathlib import Path

import pandas as pd

from training import data_sources as D
from training.common import log, parse, save_json


def build_manifest(ctx) -> pd.DataFrame:
    rng = random.Random(ctx.args.seed)
    rows = D.prepare_cifake(ctx, rng)
    rows += D.prepare_artifact(ctx, rng)
    rows += D.prepare_genimage(ctx, rng)
    rows += D.prepare_openfake(ctx, rng)          # optional: never stops the run
    if ctx.args.generator_root:
        rows += D.prepare_generator_folders(ctx, rng, Path(ctx.args.generator_root), "Generator folders")
    if not rows:
        raise SystemExit("no training images found - check the dataset options")
    df = D.dedup_and_check_leakage(pd.DataFrame(rows), ctx.reports / "leakage_check.json")
    df = D.balance(df, ctx.args.seed)
    if df.empty or df["label"].nunique() < 2:
        raise SystemExit("manifest is empty or has only one class after balancing - check the datasets")
    tmp = ctx.manifest.with_name(ctx.manifest.name + ".part")
    df.to_csv(tmp, index=False)
    tmp.replace(ctx.manifest)                     # atomic: a crash never leaves a half-written manifest behind
    log.info("manifest: %d images\n%s", len(df), df.groupby(["source", "split", "label"]).size().unstack(fill_value=0).to_string())
    if "family" in df:
        fk = df[df.label == 1]
        if len(fk):
            log.info("generator families (AI images):\n%s", fk.groupby(["family", "source"]).size().unstack(fill_value=0).to_string())
    return df


def write_datasets_info(ctx, df: pd.DataFrame, ood: pd.DataFrame | None) -> None:
    used = set(df["source"].unique())
    info = [dict(d) for d in D.DATASETS_INFO if d["name"] in used]
    counts = df.groupby("source")["split"].value_counts().unstack(fill_value=0)
    for d in info:
        if d["name"] in counts.index:
            d.update({f"n_{s}": int(counts.loc[d["name"]].get(s, 0)) for s in ("train", "val", "test")})
    if ood is not None:
        oc = ood["source"].value_counts()
        for name in ("Synthbuster", "RAISE"):
            if name in oc.index:
                d = dict(next(x for x in D.DATASETS_INFO if x["name"] == name))
                d["n_ood"] = int(oc[name])
                info.append(d)
    save_json(ctx.work / "datasets.json", info)


KAGGLE = {"CIFAKE": ("cifake_root", "birdy654/cifake-real-and-ai-generated-synthetic-images"),
          "ArtiFact": ("artifact_root", "awsaf49/artifact-dataset")}


def _missing(paths) -> int:
    return sum(not Path(p).is_file() for p in paths)


def ensure_files(ctx, df: pd.DataFrame) -> None:
    """Kaggle datasets live on Colab's LOCAL disk (~/.cache/kagglehub), which a disconnect wipes, while manifest.csv
    on Drive survives. Every resume checks a sample of each source and re-downloads what disappeared, so the later
    stages never silently train on a fraction of the data."""
    for src, g in df.groupby("source"):
        sample = g["path"].sample(n=min(60, len(g)), random_state=0).tolist()
        miss = _missing(sample)
        if not miss:
            continue
        log.warning("%s: %d of %d sampled image files are missing", src, miss, len(sample))
        if src in KAGGLE and not getattr(ctx.args, KAGGLE[src][0]):
            import kagglehub
            log.info("%s: re-downloading from Kaggle (local disk was cleared, e.g. by a Colab disconnect)", src)
            kagglehub.dataset_download(KAGGLE[src][1])
            miss = _missing(sample)
        if miss:
            raise SystemExit(f"{src}: {miss} of {len(sample)} sampled files from manifest.csv no longer exist "
                             f"(e.g. {next(p for p in sample if not Path(p).is_file())}). Restore the dataset folder, or "
                             f"rebuild everything with --force (all stages are then recomputed).")
        log.info("%s: files restored", src)


def main() -> None:
    ctx = parse("Build the training manifest")
    if ctx.manifest.exists() and not ctx.args.force:
        log.info("%s already exists - reusing (use --force to rebuild)", ctx.manifest.name)
        df = pd.read_csv(ctx.manifest)
        ensure_files(ctx, df)
    else:
        df = build_manifest(ctx)
        # outputs of later stages computed from an OLDER manifest would be silently reused -> remove them
        stale = [p for d in (ctx.features, ctx.artifacts, ctx.reports) for p in d.iterdir()
                 if p.is_file() and p.name != "leakage_check.json"]
        for p in stale:
            p.unlink()
        if stale:
            log.info("new manifest: removed %d outputs of later stages from a previous run (they will be recomputed)", len(stale))

    ood_path = ctx.work / "ood_manifest.csv"
    ood = pd.read_csv(ood_path) if ood_path.is_file() else None
    if ctx.args.with_ood and (ood is None or ctx.args.force):
        try:                                       # the OOD test is an extra - it must never stop training
            ood = D.prepare_synthbuster(ctx)
            if ood is not None:
                ood.to_csv(ood_path, index=False)
                log.info("OOD set: %s", ood.groupby(["source", "label"]).size().to_dict())
        except Exception as e:                     # noqa: BLE001
            log.warning("OOD set skipped (%s: %s)", type(e).__name__, e)

    write_datasets_info(ctx, df, ood)


if __name__ == "__main__":
    main()
