# CSST 102 — Final Project requirements ↔ where they are met

✅ done in the repo · 🟡 done but needs your input/verification · ⬜ you must do (outside the code)

## ML development requirements
| Requirement | Status | Where |
|---|---|---|
| Dataset from clearly identified source; attributes, target, size, limitations; cite | ✅ | `docs/DATASETS.md` (links, data card), `datasets.json`, model card §2 |
| Data preparation (missing/corrupt, encoding, scaling, selection) with reasons | ✅ | Model card §3; `training/common.py::open_rgb`, `app/preprocess.py`, `training/augment.py`, `training/data_sources.py::balance` |
| Splitting + validation, **leakage prevention** | ✅ | train/val/test; fusion + thresholds + model choice on **validation only**; SHA-256 duplicate check across splits (`dedup_and_check_leakage` → `leakage_check.json`); 5-fold CV (`03b_cross_validate.py`) |
| Train ≥ 1 suitable model in Python (scikit-learn etc.) | ✅ | PyTorch/timm/open_clip heads + **scikit-learn** (LogisticRegression fusion, CV, baselines) |
| Compare with baseline / alternative; justify final choice | ✅ | `07_evaluate.py` → `comparison` (majority, LR, Random Forest, each member, ensemble) + selection basis (validation AUC) |
| Metrics appropriate to task (confusion matrix, accuracy, precision, recall, F1; MAE/MSE/RMSE…) | ✅ | `training/metrics.py` (unit-tested against scikit-learn), `metrics.json` |
| Interpretation: meaning, errors, limitations, uncertainty, unreliable situations | ✅ | Auto-generated `MODEL_CARD.md` §6–7 (error analysis by size/generator, most confident mistakes), `docs/RESPONSIBLE_ML.md` |
| Reproducibility (organised, inspectable) | ✅ | numbered scripts, fixed seeds, `requirements*.txt`, `run_info.json` (versions, seed, command, git commit), `manifest.csv` shipped in the bundle |

## Web application requirements
| Requirement | Status | Where |
|---|---|---|
| Functional app connected to the trained model (no hard-coded predictions) | ✅ | Laravel → queue → FastAPI → ensemble. Without a bundle the API answers *Inconclusive*/503, never a fake number |
| Clear input form with the features the model needs | ✅ (test UI) | Upload form (`Detection.svelte`); final UI by teammates |
| Validate inputs; handle missing / invalid / out-of-range | ✅ | `ImageGuard` (type sniffing, size, dimensions), `UploadImageRequest`, 18 PHPUnit tests |
| Same preprocessing as training | ✅ | `ml-service/app/preprocess.py` is imported by both the API and training |
| Load and use the trained model for each valid submission | ✅ | `app/detectors/bundle.py` (integrity-checked) |
| Readable prediction + brief explanation | ✅ | verdict, % AI/Real, explanation, component scores, provenance findings |
| **Show evaluation results in the app** | ✅ | `GET /api/v1/model/evaluation` + `/evaluation` page (metrics, confusion matrix, ROC, comparison, errors, robustness); PDF report |
| **Notice of intended use + limitations** | ✅ | `config/hulagwai.php → notice` (served in every result, `/model/evaluation`, PDF) |
| Usable interface; common errors don't crash | ✅ / 🟡 | Test UI + JSON errors; **teammates' final UI must display the notice and handle error codes in `docs/API.md`** |
| Deployment / local instructions | ✅ | README §1 |

## Responsible ML (§4)
| Item | Status | Where |
|---|---|---|
| Privacy, bias, fairness, transparency, explainability, accountability, over-reliance; safeguards & limits | ✅ | `docs/RESPONSIBLE_ML.md` |
| No personal/confidential data without authorisation | ✅ | public datasets only; upload notice; encrypted/erasable storage |

## Submission
| Item | Status | Where |
|---|---|---|
| ZIP of complete project: source, **trained model file**, preprocessing, install instructions, config; no temp files/credentials | 🟡 | `python scripts/make_submission.py` builds it (excludes `.env`, `vendor`, `node_modules`, caches; includes `ml-service/models/current`). **You must train the model first.** |
| Dataset (if licence/size permit) or URL + instructions; notebook/scripts; which files must be generated | ✅ | `docs/DATASETS.md`, `ml-service/training/`, README "Files you must generate before running" |
| PDF documentation (instructor's template, uploaded later) | ⬜ | Use `MODEL_CARD.md`, `docs/*.md` and the PDF analysis report as source material |
| Demo / video | ⬜ | `docs/DEMO_SCRIPT.md` |
| Instructor approval of topic and scope | ⬜ | **Ask before submitting** — the guideline requires approval, and this project goes beyond a basic scikit-learn tabular model (image input, deep features). Be ready to explain why it still fits CSST 102. |
| AI-assistance acknowledgement | 🟡 | `docs/AI_ASSISTANCE.md` — edit to your instructor's policy |
| Deadline | ⚠️ | The guideline states **November 16, 2026** — confirm any extension with your instructor |
