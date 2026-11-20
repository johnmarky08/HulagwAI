"""Stage 1 - download datasets and build manifest.csv (+ ood_manifest.csv for unseen generators)."""
import random
from pathlib import Path

import pandas as pd

from training import data_sources as D
from training.common import SIZE_KEYS, log, parse, save_json


def _size_settings(ctx) -> dict:
    d = {k: ctx.prof.get(k, 0) for k in SIZE_KEYS if k not in ("freq_max", "robustness_n")}
    d["max_images"] = ctx.prof.get("max_images", 0)
    return d


def check_manifest_size(ctx) -> None:
    """A reused manifest built with other data sizes (e.g. colab_fast, then --subset 0.2) would silently ignore the
    new size - stop instead of training for hours on the wrong amount of data."""
    f = ctx.work / "manifest_settings.json"
    if not f.is_file():                           # manifest from before this check existed
        log.warning("cannot verify that the existing manifest.csv matches profile=%s%s - if it came from another "
                    "profile/--subset, use a new --work folder or --force", ctx.profile_name,
                    f" --subset {ctx.args.subset}" if ctx.args.subset else "")
        return
    import json
    old, new = json.loads(f.read_text(encoding="utf-8")), _size_settings(ctx)
    old.pop("time_limited", None)                 # written by an earlier version
    old.setdefault("max_images", 0)
    if old != new:
        diff = ", ".join(f"{k}: {old.get(k)} -> {new[k]}" for k in new if old.get(k) != new[k])
        raise SystemExit(f"manifest.csv in {ctx.work} was built with other data sizes ({diff}). Use a new --work folder "
                         f"for this profile/--subset, or add --force to rebuild here (all later stages are recomputed).")


def intended_sources(ctx) -> dict[str, str]:
    """Datasets this profile + these options are meant to train on -> how to leave one out on purpose."""
    a, p = ctx.args, ctx.prof
    want = {"CIFAKE": "CIFAKE is mandatory"}
    if p.get("artifact_per_class"):
        want["ArtiFact"] = "pass --artifact-root with the extracted dataset, or use a profile without ArtiFact"
    if p.get("genimage_per_class") and a.genimage_root:
        want["GenImage"] = "fix --genimage-root or drop it"
    if p.get("openfake_per_family") and not a.no_openfake:
        want["OpenFake"] = "re-run (the download resumes), or pass --no-openfake to train without it"
    if a.generator_root:
        want["Generator folders"] = "fix --generator-root or drop it"
    return want


def check_complete(ctx, df: pd.DataFrame) -> None:
    """Missing-data guard: every intended dataset must be in train, val AND test with real and AI images (balance()
    drops a source/split that lacks a class), no row may have empty required fields, and attribution must have the
    families it needs. A run never trains silently on a fraction of what was intended."""
    problems, warnings = [], []                  # problems stop the run; warnings are logged and training continues
    empty = df[["path", "label", "source", "split"]].isna().any(axis=1)
    if empty.any():
        problems.append(f"{int(empty.sum())} manifest rows have an empty path/label/source/split")
    for src, fix in intended_sources(ctx).items():
        have = set(df.loc[df.source == src, "split"])
        miss = [s for s in ("train", "val", "test") if s not in have]
        if miss:
            msg = f"{src}: no balanced real+AI images in {', '.join(miss)} - {fix}"
            # only the mandatory dataset is fatal; an optional one missing some splits just contributes less
            (problems if src == "CIFAKE" else warnings).append(msg)
    gen_sources = {"ArtiFact", "OpenFake", "GenImage", "Generator folders"} & set(intended_sources(ctx))
    if gen_sources and "family" in df:
        fk = df[(df.label == 1) & (df.split == "train") & df["attr_ok"].astype(bool) & df["family"].notna()]
        counts = fk["family"].value_counts()
        ok = counts[counts >= ctx.prof["attr_min"]]
        if len(ok) < 2:                           # stage 06b skips attribution itself in this case
            warnings.append(f"generator attribution needs >= 2 families with >= {ctx.prof['attr_min']} training images, "
                            f"got {counts.to_dict()} - attribution will be skipped (re-run so OpenFake/ArtiFact finish "
                            f"downloading to enable it)")
    if problems:
        raise SystemExit("training data incomplete:\n  - " + "\n  - ".join(problems) +
                         "\nNothing was trained. Fix the above and re-run (add --force if manifest.csv already exists).")
    if warnings:
        log.warning("training data incomplete - continuing anyway:\n  - %s", "\n  - ".join(warnings))
    else:
        log.info("completeness check passed: %s present in train/val/test", ", ".join(intended_sources(ctx)))


def build_manifest(ctx) -> pd.DataFrame:
    rng = random.Random(ctx.args.seed)
    rows = D.prepare_cifake(ctx, rng)
    rows += D.prepare_artifact(ctx, rng)
    rows += D.prepare_genimage(ctx, rng)
    rows += D.prepare_openfake(ctx, rng)          # download problems are warnings; check_complete() decides
    if ctx.args.generator_root:
        rows += D.prepare_generator_folders(ctx, rng, Path(ctx.args.generator_root), "Generator folders")
    if not rows:
        raise SystemExit("no training images found - check the dataset options")
    df = D.dedup_and_check_leakage(pd.DataFrame(rows), ctx.reports / "leakage_check.json")
    df = D.balance(df, ctx.args.seed)                                  # real = AI in every source/split
    df = D.cap_total(df, ctx.prof.get("max_images", 0), ctx.args.seed, ctx.prof["attr_min"])
    if df.empty or df["label"].nunique() < 2:
        raise SystemExit("manifest is empty or has only one class after balancing - check the datasets")
    for sp in ("train", "val", "test"):
        if not (df["split"] == sp).any():
            raise SystemExit(f"manifest has no '{sp}' images after balancing - check the datasets")
    D.check_balance(df, ctx.reports / "balance_check.json")
    check_complete(ctx, df)
    tmp = ctx.manifest.with_name(ctx.manifest.name + ".part")
    df.to_csv(tmp, index=False)
    tmp.replace(ctx.manifest)                     # atomic: a crash never leaves a half-written manifest behind
    save_json(ctx.work / "manifest_settings.json", _size_settings(ctx))
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
    on Drive survives. Every resume checks EVERY file of the manifest and re-downloads what disappeared, so the later
    stages never silently train on a fraction of the data."""
    for src, g in df.groupby("source"):
        paths = g["path"].tolist()
        miss = _missing(paths)
        if not miss:
            continue
        log.warning("%s: %d of %d image files are missing", src, miss, len(paths))
        art = ctx.work / "artifact"
        if src == "ArtiFact" and not ctx.args.artifact_root and all(Path(q).is_relative_to(art) for q in paths):
            log.info("ArtiFact: re-downloading the %d missing files only", miss)
            kf = D.KaggleFiles(D.ARTIFACT_HANDLE, art)
            kf.get_many([Path(q).relative_to(art).as_posix() for q in paths if not Path(q).is_file()])
            miss = _missing(paths)
        elif src in KAGGLE and not getattr(ctx.args, KAGGLE[src][0]):
            import kagglehub
            log.info("%s: re-downloading from Kaggle (local disk was cleared, e.g. by a Colab disconnect)", src)
            kagglehub.dataset_download(KAGGLE[src][1])
            miss = _missing(paths)
        if miss:
            raise SystemExit(f"{src}: {miss} of {len(paths)} files from manifest.csv no longer exist "
                             f"(e.g. {next(p for p in paths if not Path(p).is_file())}). Restore the dataset folder, or "
                             f"rebuild everything with --force (all stages are then recomputed).")
        log.info("%s: files restored", src)
    log.info("all %d manifest files present", len(df))


def ood_problems(ctx, ood: pd.DataFrame | None) -> list[str]:
    """What is missing from the requested unseen-generator test set (--with-ood, --raise-csv, --ood-real-dir)."""
    if ood is None or ood.empty:
        return ["no Synthbuster images (Zenodo unreachable or not enough free disk space - see the warnings above)"]
    probs = []
    if not ((ood.label == 1) & (ood.source == "Synthbuster")).any():
        probs.append("no Synthbuster AI images")
    if (ctx.args.raise_csv or ctx.args.ood_real_dir) and not (ood.label == 0).any():
        probs.append("no real photos from --raise-csv / --ood-real-dir")
    missing = int((~ood["path"].map(lambda q: Path(q).is_file())).sum())
    if missing:
        probs.append(f"{missing} OOD image files listed in ood_manifest.csv no longer exist")
    return probs


def main() -> None:
    ctx = parse("Build the training manifest")
    if ctx.manifest.exists() and not ctx.args.force:
        log.info("%s already exists - reusing (use --force to rebuild)", ctx.manifest.name)
        check_manifest_size(ctx)
        df = pd.read_csv(ctx.manifest)
        ensure_files(ctx, df)
        D.check_balance(df, ctx.reports / "balance_check.json")   # a manifest from an older version is re-validated
        check_complete(ctx, df)
    else:
        df = build_manifest(ctx)
        # outputs of later stages computed from an OLDER manifest would be silently reused -> remove them
        stale = [p for d in (ctx.features, ctx.artifacts, ctx.reports) for p in d.iterdir()
                 if p.is_file() and p.name not in ("leakage_check.json", "balance_check.json")]
        for p in stale:
            p.unlink()
        if stale:
            log.info("new manifest: removed %d outputs of later stages from a previous run (they will be recomputed)", len(stale))

    ood_path = ctx.work / "ood_manifest.csv"
    ood = pd.read_csv(ood_path) if ood_path.is_file() else None
    if ctx.args.with_ood and (ood is None or ctx.args.force or ood_problems(ctx, ood)):
        try:
            ood = D.prepare_synthbuster(ctx)       # resumable: finished/extracted files are reused
            if ood is not None:
                ood.to_csv(ood_path, index=False)
                log.info("OOD set: %s", ood.groupby(["source", "label"]).size().to_dict())
        except Exception as e:                     # noqa: BLE001 - reported by the check below
            log.warning("OOD download failed (%s: %s)", type(e).__name__, e)

    write_datasets_info(ctx, df, ood)
    if ctx.args.with_ood:
        probs = ood_problems(ctx, ood)
        if probs:                                  # an extra evaluation only - never blocks training
            log.warning("unseen-generator test set incomplete - training continues, the report will omit what is "
                        "missing:\n  - %s\nRe-run the same command later to retry only the download (finished stages "
                        "are skipped).", "\n  - ".join(probs))


if __name__ == "__main__":
    main()
