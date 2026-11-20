"""Builds MODEL_CARD.md from the real metrics.json (so the written analysis can never disagree with the numbers)."""
from __future__ import annotations

import json

from training.common import Ctx


def _p(v, d=1):  return "n/a" if v is None else f"{v * 100:.{d}f}%"
def _n(v, d=4):  return "n/a" if v is None else f"{v:.{d}f}"


def build(ctx: Ctx) -> str:
    mp = ctx.reports / "metrics.json"
    if not mp.is_file():
        raise SystemExit("metrics.json missing - run training.07_evaluate first")
    m = json.loads(mp.read_text())
    t, sel = m["test"], m.get("selective") or {}
    cm = t["confusion"]
    L: list[str] = []
    add = L.append

    add(f"# HulagwAI model card — v{ctx.args.version}\n")
    add(f"_Generated automatically from `metrics.json` ({m['generated_at']}), training profile `{m['profile']}`. Numbers below are measured, not estimated._\n")
    add("## 1. Problem & intended use\n"
        "**Task:** binary classification of an uploaded image — *AI-generated (1)* vs *real (0)* — with a third reporting outcome, *Inconclusive*, when evidence is weak.  \n"
        "**Intended users:** students, journalists and general users who want a *second opinion* on whether an image is synthetic.  \n"
        "**Input:** one JPG/PNG/WEBP image (≤ 5 MB). **Output:** P(AI), a verdict, a confidence, and an explanation.  \n"
        "**Not for:** automated moderation, legal/forensic proof, disciplinary or hiring decisions, or judging a person.\n")

    add("## 2. Data\n")
    add("| Dataset | Role | Train | Val | Test | Source |\n|---|---|---:|---:|---:|---|")
    for d in m.get("datasets", []):
        add(f"| {d['name']} | {d['role']} | {d.get('n_train', '–')} | {d.get('n_val', '–')} | {d.get('n_test', '–')} | {d['url']} |")
    add("\n**Target:** `label` (1 = AI-generated, 0 = real). **Attributes:** image pixels (+ file metadata for the provenance check).  \n"
        "**Known limitations:** CIFAKE images are 32×32 and from one generator (Stable Diffusion 1.4); real/fake classes differ in format in some datasets (handled by identical random degradations); public datasets do not cover the newest generators.\n")

    add("## 3. Preparation, splitting and leakage control\n"
        "* **Cleaning:** unreadable files skipped; images converted to RGB (transparency flattened on white).  \n"
        "* **Balancing:** equal real/fake counts inside every (dataset, split) so the dataset name cannot be used as a clue.  \n"
        "* **Scaling/normalisation:** per-model mean/std normalisation (CLIP / ImageNet statistics); the frequency features are standardised with *training-set* mean/std only.  \n"
        "* **Resolution policy:** ≥ 224 px → native-resolution crops (no resizing); < 224 px → bicubic up-scaling (flagged as a warning).  \n"
        "* **Augmentation (train only, both classes equally):** random blur, down/up-scaling and JPEG re-compression.  \n"
        "* **Splits:** train / validation / test (CIFAKE keeps its official test set). Fusion weights, thresholds and model selection use **validation only**; **test is evaluated once**.  \n")
    lk = m.get("leakage_check")
    if lk:
        add(f"* **Leakage check:** {lk['images_before']} → {lk['images_after']} images after removing exact duplicates; "
            f"{lk['hashes_in_multiple_splits']} images appeared in more than one split (kept in the strongest split only), "
            f"{lk['label_conflicts_removed']} label conflicts removed. *Near*-duplicates (resized or re-encoded copies) are not detected.\n")

    add("## 4. Model comparison\n")
    add("| Model | Type | Accuracy | Precision | Recall | F1 | ROC-AUC (test) | ROC-AUC (validation) |\n|---|---|---:|---:|---:|---:|---:|---:|")
    for r in m["comparison"]["rows"]:
        mark = " **← selected**" if r["family"] == "final" else ""
        add(f"| {r['name']}{mark} | {r['family']} | {_p(r['accuracy'])} | {_p(r['precision'])} | {_p(r['recall'])} | {_n(r['f1'])} | {_n(r['roc_auc'])} | {_n(r['val_roc_auc'])} |")
    add(f"\n**Selection basis:** {m['comparison']['basis']}\n")

    add("## 5. Evaluation (held-out test split)\n")
    add(f"n = {t['n']}, decision threshold {t['threshold']}.\n")
    add("| Metric | Value | Metric | Value |\n|---|---:|---|---:|")
    pairs = [("Accuracy", _p(t["accuracy"], 2), "ROC-AUC", _n(t["roc_auc"])), ("Precision", _p(t["precision"], 2), "Average precision", _n(t["average_precision"])),
             ("Recall", _p(t["recall"], 2), "MAE", _n(t["mae"])), ("Specificity", _p(t["specificity"], 2), "MSE / RMSE", f"{_n(t['mse'])} / {_n(t['rmse'])}"),
             ("F1", _n(t["f1"]), "Brier score", _n(t["brier"])), ("Balanced accuracy", _p(t["balanced_accuracy"], 2), "Log loss", _n(t["log_loss"])),
             ("MCC", _n(t["mcc"]), "ECE (calibration)", _n(t["ece"]))]
    for a, b, c, d in pairs:
        add(f"| {a} | {b} | {c} | {d} |")
    add(f"\n**Confusion matrix** — TN {cm['tn']}, FP {cm['fp']}, FN {cm['fn']}, TP {cm['tp']}.\n")
    cv = m.get("cross_validation")
    if cv:
        add(f"**5-fold cross-validation** (CLIP-feature classifier, training split): accuracy {_p(cv['accuracy']['mean'], 2)} ± {_p(cv['accuracy']['std'], 2)}, ROC-AUC {_n(cv['roc_auc']['mean'])} ± {_n(cv['roc_auc']['std'])}.\n")
    if sel:
        add(f"**Three-way verdict:** the model commits on {_p(sel['coverage'])} of images (Inconclusive on {_p(sel['inconclusive_rate'])}); accuracy on the committed ones is {_p(sel['accuracy_decided'], 2)}.\n")

    add("### Robustness (accuracy after transformations)\n")
    add("| Transformation | Accuracy | n |\n|---|---:|---:|")
    for k, v in m["robustness"].items():
        add(f"| {k.replace('_', ' ')} | {_p(v['accuracy'])} | {v['n']} |")
    if m.get("ood"):
        o = m["ood"]
        add(f"\n### Unseen generators — {o['name']}\nDetection rate (recall) on {o['n_fake']} AI images: **{_p(o['recall'])}**; "
            + (f"specificity on {o['n_real']} real images: **{_p(o['specificity'])}**." if o.get("n_real") else "no real photos were supplied, so false-positive behaviour on this set was **not measured**."))

    am = m.get("attribution")
    if am and am.get("test"):
        at = am["test"]
        add("\n## 5b. Generator attribution (which AI family?)\n")
        add(f"Closed set of {len(am['families'])} families: " + ", ".join(am["labels"].values()) + ". "
            f"Chance level {_p(at['chance_level'])}. The model answers *unknown* when its confidence is below τ = {am['tau']}.\n")
        add("| Metric | Value |\n|---|---:|")
        for k, v in (("Accuracy", _p(at["accuracy"], 2)), ("Top-3 accuracy", _p(at["top3_accuracy"], 2)), ("Macro-F1", _n(at["macro_f1"])),
                     ("Coverage (answered)", _p(at["coverage"])), ("Accuracy when answered", _p(at["accuracy_when_accepted"], 2)), ("ECE", _n(at["ece"]))):
            add(f"| {k} | {v} |")
        add("\n| Family | n | Precision | Recall | F1 |\n|---|---:|---:|---:|---:|")
        for fam, r in at["per_family"].items():
            add(f"| {am['labels'].get(fam, fam)} | {r['n']} | {_p(r['precision'])} | {_p(r['recall'])} | {_n(r['f1'])} |")
        if am.get("dropped_families"):
            add(f"\nFamilies left out for lack of training images: {am['dropped_families']}.")
        if am.get("ood"):
            add("\n**Unseen generators:** " + "; ".join(f"{g}: answered {_p(r['answered_rate'])}, most often predicted {r['most_common_prediction']}"
                                                         + (f", accuracy {_p(r['accuracy'])}" if 'accuracy' in r else " (family not in training)")
                                                         for g, r in am["ood"]["per_generator"].items()) + ".")
        add(f"\n{am['note']}\n")

    add("\n## 6. What the results mean (interpretation)\n")
    add(f"* **Recall {_p(t['recall'])}** → of 100 AI-generated test images the system flags about {t['recall'] * 100:.0f}; the other {(1 - t['recall']) * 100:.0f} slip through (false negatives).  \n"
        f"* **Specificity {_p(t['specificity'])}** → about {(1 - t['specificity']) * 100:.0f} of 100 real images are wrongly flagged as AI (false positives) — the costlier error when the result may be used to accuse someone.  \n"
        f"* **Precision {_p(t['precision'])}** → when it says “AI”, it is right that often *on a balanced test set*. With real-world base rates (e.g. few AI images) precision will be lower.  \n"
        f"* **MAE {_n(t['mae'])} / Brier {_n(t['brier'])} / ECE {_n(t['ece'])}** describe the quality of the probabilities: lower is better; an ECE near 0 means a displayed “80 %” is right about 80 % of the time.  \n"
        "* The displayed *confidence* is how strongly the model favours its answer — **not** the probability that the image is authentic.\n")
    er = m["errors"]
    add("### Error analysis\n")
    add("| Image size | n | Accuracy |\n|---|---:|---:|")
    for k, v in er["by_resolution"].items():
        add(f"| {k} | {v['n']} | {_p(v['accuracy'])} |")
    if er["false_positives_by_source"]:
        add(f"\nFalse positives by dataset: {er['false_positives_by_source']}.")
    if er["false_negatives_by_generator"]:
        add(f"\nMissed AI images by generator: {er['false_negatives_by_generator']}.")
    if er["most_confident_mistakes"]:
        add("\nMost confident mistakes (file, dataset/generator, true label, P(AI)):\n")
        for x in er["most_confident_mistakes"]:
            add(f"* `{x['file']}` — {x['source']}/{x['generator']} — label {x['label']} — P(AI) {x['p_ai']}")
    add("\n## 7. Limitations & when predictions are unreliable\n"
        "* Very small (< 64 px), heavily compressed, screenshotted, re-photographed or heavily edited images.  \n"
        "* Generators newer than the training data (check the unseen-generator result above).  \n"
        "* Stripped or forged metadata: absence of provenance data proves nothing, and camera EXIF can be copied onto a synthetic image — it is therefore never used to lower the score.  \n"
        "* A partly AI-edited real photo (inpainting, face swap) may be judged as real.  \n"
        "* Results can differ across skin tones, art styles and content types that are under-represented in the datasets (see RESPONSIBLE_ML.md).  \n"
        "* Generator attribution only knows the families listed in §5b; a new or unlisted generator may be named confidently and wrongly.  \n"
        "* The \"why it looks AI\" evidence lists detector signals and a heat map of where the pixel model fires. It does **not** detect specific defects "
        "(extra fingers, garbled text); a highlighted region is not a verified flaw.\n")
    add("## 8. Reproducibility\nSee `run_info.json` (versions, seed, command), `manifest.csv` (exact images and splits), `leakage_check.json`, `cv_clip.json`, and the numbered scripts in `ml-service/training/`.\n")
    return "\n".join(L)
