# Training the HulagwAI model

Runs on **Google Colab (free T4 GPU)**. The scripts are numbered stages; `run_all` executes them in order and every stage skips itself when its output already exists (safe after a disconnect).

| Stage | File | What it does | Output (in `--work`) |
|---|---|---|---|
| 1 | `01_prepare_data.py` | downloads CIFAKE (+ ArtiFact, GenImage, Synthbuster), **removes exact duplicates across splits (leakage check)**, builds a **balanced** train/val/test manifest | `manifest.csv`, `datasets.json`, `ood_manifest.csv` |
| 2 | `02_extract_clip_features.py` | frozen CLIP encoder → cached features (clean + degraded views) | `features/*.npz` |
| 3 | `03_train_clip_head.py` | linear head (regularisation picked on validation) | `artifacts/clip_head.safetensors` |
| 3b | `03b_cross_validate.py` | 5-fold stratified cross-validation (scikit-learn) on the training split | `reports/cv_clip.json` |
| 4 | `04_train_cnn.py` | fine-tune ConvNeXt on native-resolution crops (AMP, best epoch kept) | `artifacts/cnn.safetensors` |
| 5 | `05_train_frequency.py` | spectrum / noise-residual MLP | `artifacts/freq_mlp.safetensors` |
| 6 | `06_fit_fusion.py` | logistic-regression fusion + Real/Inconclusive/AI thresholds, **validation only** | `artifacts/fusion.json` |
| 6b | `06b_train_attribution.py` | **which AI family?** softmax head on the CLIP + CNN embeddings; temperature scaling and an "unknown" threshold fitted on validation; test + Synthbuster reported | `artifacts/attribution_head.safetensors`, `reports/attribution_metrics.json` |
| 7 | `07_evaluate.py` | held-out **test** metrics, per dataset/generator, robustness, unseen generators | `reports/metrics.json` — includes **baseline comparison** (majority, scikit-learn LR + Random Forest, each member, ensemble), ROC/calibration, error analysis |
| 8 | `08_export_bundle.py` | assemble + hash + smoke-load + zip | `hulagwai-ensemble-<version>.zip` (+ `provenance/`: manifest.csv, run_info.json, MODEL_CARD.md) |

## Step by step
1. Colab ▸ `File ▸ Upload notebook` → `training/HulagwAI_Colab.ipynb` (or open it from GitHub). `Runtime ▸ Change runtime type ▸ T4 GPU`.
2. Put the code on Colab: upload `ml-service.zip` to Drive **or** `git clone` your repo (cell 2 has both options).
3. Kaggle key → Colab *Secrets*: `KAGGLE_USERNAME`, `KAGGLE_KEY` (Kaggle ▸ Settings ▸ API ▸ Create New Token).
4. Run the **smoke** profile first: `!python -m training.run_all --profile smoke --work /content/smoke`. It uses random weights and tiny data → numbers are meaningless, but it proves every stage runs.
5. Real run:
   ```bash
   !python -m training.run_all --profile colab_fast --work /content/drive/MyDrive/hulagwai_work --version 1.0.0 --with-ood
   ```
6. Download the zip, unzip into `ml-service/models/current/`, run `python -m app.verify`.

## Profiles & flags
| Profile | Data per class (CIFAKE / ArtiFact / GenImage) | CNN epochs | Use |
|---|---|---|---|
| `smoke` | 60 / 0 / 0 | 1 | plumbing test |
| `colab_fast` | 10 000 / 20 000 / 15 000 | 4 | recommended first model |
| `colab_full` | 15 000 / 40 000 / 40 000 | 6 | best quality, longest |

`--generator-root DIR` (your own `DIR/<generator>/*.png` + `DIR/real/`) · `--no-openfake` (skip the OpenFake download) · `--genimage-root DIR` (GenImage subset on Drive) · `--artifact-root DIR` (already-downloaded ArtiFact) · `--with-ood` (download Synthbuster for the unseen-generator test) · `--raise-csv FILE` (a RAISE CSV such as `RAISE_2k.csv` — RAISE is distributed as a CSV of download links, not a folder; `--raise-n` photos (default 300) are downloaded from its `TIFF` column, converted to lossless PNG ≤ `--raise-max-side` px (default 2048) and used as the real photos of that test) · `--ood-real-dir DIR` (a folder of your own real photos for that test; without real photos only fake-detection recall is reported) · `--openfake-config NAME` (default `core`) · `--clip-arch ViT-L-14` (stronger, slower, needs more RAM when serving) · `--force` (redo a stage) · `--allow-cpu` (force all stages without a GPU — days on Colab's CPU, not recommended).

**No GPU?** `run_all` then runs only stage 1 (downloads) and stage 5 (frequency model, CPU-only anyway), saves them in `--work` and stops; run the same command again on a GPU runtime to continue.

## Why it is built this way (for your defense)
* **Why an ensemble:** three independent views (semantic CLIP features, pixel artefacts, spectrum) fail in different ways; fusing them and measuring their *disagreement* gives an honest "Inconclusive".
* **Why native-resolution crops:** down-sizing a photo to 224 px destroys the high-frequency traces detectors rely on.
* **Why the same degradations on both classes:** otherwise the model can learn dataset shortcuts (JPEG vs PNG, resolution) instead of generator artefacts, and collapses on WhatsApp/Facebook-style recompression.
* **Why Synthbuster is test-only and thresholds use validation only:** the reported numbers are never tuned on the data they are measured on.
* **What the metrics mean:** MAE/MSE/RMSE/Brier/log-loss/ECE measure the quality of the *probabilities* (|P(AI) − label|), accuracy/precision/recall/F1/MCC measure the 0.5-threshold decisions, `selective` measures the 3-way verdict (coverage vs. accuracy when decided).

## Generator attribution data
OpenFake is downloaded from Hugging Face in stage 1 by reading its parquet files directly — first only the small label/model columns, then the image bytes of the rows that are kept, a few at a time (peak RAM ≈ 200 MB, safe on free Colab; `datasets` streaming used several GB and crashed the session) (`openfake_per_family` images per family: 4 000 for `colab_fast`, 8 000 for `colab_full`, plus as many real photos; the original file bytes are kept. CIFAKE is deliberately small: its 32×32 images are unlike real uploads and would otherwise dominate validation, i.e. the fusion weights and thresholds). Needs `pyarrow` and `huggingface_hub` (in `requirements-train.txt`). Expect a large download; it is saved in `<work>/openfake/`, resumes after a Colab disconnect and stops at `--openfake-max-gb` (default 25 GB), at `--openfake-max-minutes` (default 120) or when less than `--min-free-gb` (default 4 GB) is free on Drive. Any OpenFake failure is a warning, never a crash. If the dataset's column names change, stage 1 logs the columns it found and continues without OpenFake — adjust `prepare_openfake()` in `data_sources.py`. ArtiFact and GenImage also carry generator names and feed attribution automatically. Optional: add a free Hugging Face **Read** token as Colab secret `HF_TOKEN` (the notebook picks it up). It gives the download its own rate limit instead of Colab's shared one; nothing is billed. If the token is rejected (401/403) the download continues anonymously; if its rate limit is used up (429) it switches to anonymous at once, and if that is limited too it waits and then retries with the token. The token is never written to the logs.

## Troubleshooting
* *CUDA out of memory in stage 4* → lower `cnn_batch` in `common.py` (profile) to 32.
* *Disk full* → ArtiFact is huge; use `--artifact-root` with a subset, or reduce `artifact_per_class`.
* *Colab disconnected* → just re-run the same cell; finished stages are skipped.
* *"ArtiFact/GenImage: cannot find …"* → the adapter printed the columns/folders it found; adjust `data_sources.py` accordingly (those adapters could not be tested against the real data when written).
* Unit tests for the numpy parts (metrics, fusion): `pytest` in `ml-service/`.
