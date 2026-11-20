# Demonstration / video script (CSST 102 · Submission §4)

Every member should present one block and be ready for questions. Total ≈ 8–10 min.

| # | Presenter | What to show / say | Where it is in the project |
|---|---|---|---|
| 1 | _member_ | **Problem & users**: why detecting AI images matters; intended use & non-use; classification task. | `docs/RESPONSIBLE_ML.md` §1, model card §1 |
| 2 | _member_ | **Dataset**: CIFAKE + ArtiFact + GenImage (+ Synthbuster for unseen generators): size, target, limits, citations. Show `manifest.csv`, `leakage_check.json`. | `docs/DATASETS.md`, training stage 1 |
| 3 | _member_ | **Preprocessing & splitting**: RGB conversion, native-resolution crops, balancing, degradations, duplicate/leakage check, val-only tuning, CV. | `ml-service/app/preprocess.py`, `training/01…03b` |
| 4 | _member_ | **Models & comparison**: majority baseline → scikit-learn LR/RF → CLIP head / ConvNeXt / frequency → ensemble; why the ensemble was selected (validation AUC). | `training/07_evaluate.py`, Evaluation page |
| 5 | _member_ | **Evaluation & interpretation**: confusion matrix, precision/recall/F1/AUC/MAE, ROC, robustness, error analysis, unseen generators. Say what the numbers mean for a real user. | `/evaluation`, `MODEL_CARD.md` |
| 6 | _member_ | **Live demo — valid inputs**: (a) a real camera photo, (b) an AI image from a generator, (c) an image with embedded generator metadata (e.g. a Stable Diffusion WebUI PNG) → provenance finding, (d) a tiny / heavily compressed image → *Inconclusive* + warning. Show the progress screen, result, **Likely generator** card (top-3 families, “unknown” when unsure, “Named in file” for metadata) and **Why it may look AI** card (signals + heat-map toggle), PDF report, history. Say clearly that the evidence does not detect specific defects like extra fingers. | `/detect`, `/history` |
| 7 | _member_ | **Invalid inputs**: a `.gif`, a renamed text file (`evil.png`), an image > 5 MB, a 6th rapid upload (rate limit) → clear error messages, no crash. | `ImageGuard`, tests |
| 8 | _member_ | **How the model is connected**: Laravel → queue → FastAPI `/v1/analyze` → same `preprocess.py` as training → bundle verified by SHA-256. Show `python -m app.verify`. | `docs/API.md`, `ml-service/app/` |
| 9 | _member_ | **Responsible ML & security**: privacy model (guest vs account, encryption), bias/limits, OWASP mapping, human-in-the-loop advice. | `docs/RESPONSIBLE_ML.md`, `docs/SECURITY.md` |

**Sample inputs to prepare before recording** (do not commit copyrighted images): 2 real photos you took, 2 AI images you generated yourself, 1 SD-WebUI PNG with metadata, 1 low-res/JPEG-recompressed image, 1 invalid file of each kind above.
**Tip:** run `php artisan test` and `pytest` on camera to show the test suites pass.
