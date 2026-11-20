# Responsible machine learning — HulagwAI

*(CSST 102 · Guideline §4)* Applies to the model, the data and the web application.

## 1. Possible harms of this system
| Concern | Why it matters here | Safeguard in the project |
|---|---|---|
| **False accusation** (real image flagged AI) | Someone's genuine photo or artwork could be dismissed as fake or they could be accused of deception. This is the costliest error. | Three-way verdict with an *Inconclusive* band tuned for ≥ 97 % precision on validation; specificity and false-positive rate reported; the UI/PDF repeat "prediction, not proof". |
| **Missed fakes** (AI image judged real) | A false "real" can give a fake image credibility. | Recall reported per generator and on unseen generators; absence of detection is never worded as "authentic". |
| **Wrong generator named** | Saying "made with Midjourney" can wrongly implicate a person, tool or vendor. | Families only, top-3 shown with probabilities, abstains ("unknown") below a validated confidence τ, metadata-declared names shown separately; disclaimer on every result and in the PDF. |
| **Invented explanations** | Free-text "the hand has 8 fingers" style reasons from AI models are often hallucinated. | Evidence is limited to measurable signals (detector scores, provenance markers, a patch heat map) and always labelled "not a verified defect". No cloud AI is used, so images never leave the machine. |
| **Over-reliance on automation** | Users may treat a percentage as truth. | The score is explicitly "how strongly the model favours its prediction, not the probability that the image is authentic"; every result carries intended-use + limitation text; the PDF contains the full metrics. |
| **Bias / fairness** | The datasets are dominated by certain content (CIFAR-10 object classes, ImageNet photos, specific art styles). Accuracy can differ for faces/skin tones, non-Western art styles, illustrations, low-end cameras or heavily edited photos, which the data under-represents. | Per-dataset and per-generator breakdowns, error analysis by image size; the limitation is stated openly. **Not measured:** per-demographic accuracy (no demographic labels exist in the data) — do not claim fairness across groups. |
| **Data privacy** | Users upload images that may show people, minors or private places. | Guests: encrypted temp copy deleted right after analysis, only result + thumbnail in the encrypted session. Users: images stored encrypted (XChaCha20-Poly1305), filenames AES-256; per-user quota; delete one / clear all / delete account (full erasure). IPs stored only as HMAC. Upload notice tells users not to submit others' private images or IDs. No training on user uploads. |
| **Training-data licensing / consent** | Datasets contain images of people and copyrighted works. | Only public research datasets are used, cited with links (docs/DATASETS.md); no personal or confidential data was collected for this project. Check each licence before redistributing data. |
| **Security misuse** | The detector's output could be used to *tune* fakes until they pass. | Rate limits, no exposure of raw component logits beyond what the UI needs, model version recorded. Residual risk acknowledged: any public detector can be probed. |

## 2. Transparency & explainability
* Every result lists the **three model components** (CLIP, CNN, frequency) with their individual probabilities and the **provenance findings** (e.g. "Stable Diffusion WebUI parameters embedded"), plus warnings (low resolution, heavy compression).
* The model card (`MODEL_CARD.md`, auto-generated from the real metrics) documents data, splits, leakage checks, model comparison, errors and limits.
* **Limits of explainability:** deep models are not fully interpretable; the system does *not* highlight which pixels drove the decision. Treat component scores as indications, not causal explanations.

## 3. Accountability
* Each analysis stores the **model name, version and weights hash**, so any decision can be traced to the exact model that produced it.
* `audit_logs` records security-relevant events (no filenames, no emails, hashed IPs).
* The authors are responsible for verifying and being able to explain all submitted code and results; AI assistance is acknowledged in `docs/AI_ASSISTANCE.md`.

## 4. Recommended limits on use
1. Use as one signal among several (reverse image search, source checking, provenance tools such as C2PA).
2. Never use a verdict alone for discipline, hiring, legal or moderation decisions about people.
3. Re-evaluate and retrain when new generators appear; check the unseen-generator results in the model card before trusting results on new models.
4. Do not claim the model "guarantees" authenticity or fakery.
5. Obtain consent before analysing images of identifiable people.

## 5. Known limitations (summary)
Small/compressed/edited images · generators newer than the data · partial AI edits · forged or stripped metadata · no per-demographic evaluation · near-duplicate leakage not detected · C2PA signatures detected but not cryptographically verified.
