# Training the HulagwAI model

Runs on **Google Colab (free T4 GPU)**. The scripts are numbered stages; `run_all` executes them in order and every stage skips itself when its output already exists (safe after a disconnect).

| Stage | File | What it does | Output (in `--work`) |
|---|---|---|---|
| 1 | `01_prepare_data.py` | downloads CIFAKE (+ ArtiFact, GenImage, Synthbuster), builds a **balanced** train/val/test manifest | `manifest.csv`, `datasets.json`, `ood_manifest.csv` |
| 2 | `02_extract_clip_features.py` | frozen CLIP encoder → cached features (clean + degraded views) | `features/*.npz` |
| 3 | `03_train_clip_head.py` | linear head (regularisation picked on validation) | `artifacts/clip_head.safetensors` |
| 4 | `04_train_cnn.py` | fine-tune ConvNeXt on native-resolution crops (AMP, best epoch kept) | `artifacts/cnn.safetensors` |
| 5 | `05_train_frequency.py` | spectrum / noise-residual MLP | `artifacts/freq_mlp.safetensors` |
| 6 | `06_fit_fusion.py` | logistic-regression fusion + Real/Inconclusive/AI thresholds, **validation only** | `artifacts/fusion.json` |
| 7 | `07_evaluate.py` | held-out **test** metrics, per dataset/generator, robustness, unseen generators | `reports/metrics.json` |
| 8 | `08_export_bundle.py` | assemble + hash + smoke-load + zip | `hulagwai-ensemble-<version>.zip` |

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
| `colab_fast` | 40 000 / 15 000 / 15 000 | 3 | recommended first model |
| `colab_full` | 60 000 / 40 000 / 40 000 | 5 | best quality, longest |

`--genimage-root DIR` (GenImage subset on Drive) · `--artifact-root DIR` (already-downloaded ArtiFact) · `--with-ood` (download Synthbuster for the unseen-generator test) · `--ood-real-dir DIR` (real photos for that test; without them only fake-detection recall is reported) · `--clip-arch ViT-L-14` (stronger, slower, needs more RAM when serving) · `--force` (redo a stage).

## Why it is built this way (for your defense)
* **Why an ensemble:** three independent views (semantic CLIP features, pixel artefacts, spectrum) fail in different ways; fusing them and measuring their *disagreement* gives an honest "Inconclusive".
* **Why native-resolution crops:** down-sizing a photo to 224 px destroys the high-frequency traces detectors rely on.
* **Why the same degradations on both classes:** otherwise the model can learn dataset shortcuts (JPEG vs PNG, resolution) instead of generator artefacts, and collapses on WhatsApp/Facebook-style recompression.
* **Why Synthbuster is test-only and thresholds use validation only:** the reported numbers are never tuned on the data they are measured on.
* **What the metrics mean:** MAE/MSE/RMSE/Brier/log-loss/ECE measure the quality of the *probabilities* (|P(AI) − label|), accuracy/precision/recall/F1/MCC measure the 0.5-threshold decisions, `selective` measures the 3-way verdict (coverage vs. accuracy when decided).

## Troubleshooting
* *CUDA out of memory in stage 4* → lower `cnn_batch` in `common.py` (profile) to 32.
* *Disk full* → ArtiFact is huge; use `--artifact-root` with a subset, or reduce `artifact_per_class`.
* *Colab disconnected* → just re-run the same cell; finished stages are skipped.
* *"ArtiFact/GenImage: cannot find …"* → the adapter printed the columns/folders it found; adjust `data_sources.py` accordingly (those adapters could not be tested against the real data when written).
* Unit tests for the numpy parts (metrics, fusion): `pytest` in `ml-service/`.
