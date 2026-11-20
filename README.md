# HulagwAI — AI-generated image detection

> **Húlad** (copy / imitate) + **dágway** (face / form) — _a copy of a form_.
> Upload an image; HulagwAI predicts whether it is **likely AI-generated, likely real, or inconclusive**, with a confidence score, an explanation and a downloadable PDF report.

```
Browser ──► Laravel 12 (auth, validation, MySQL, encryption, queue, PDF)
                │  HTTP, loopback only, shared-secret header
                ▼
           ML service (Python / FastAPI) ── ensemble: CLIP ViT head + ConvNeXt + frequency MLP
                                          └─ provenance check: C2PA / IPTC / EXIF / PNG-chunk generator signatures
```

| Folder                                                | What lives there                         | Who touches it |
| ----------------------------------------------------- | ---------------------------------------- | -------------- |
| `app/`, `routes/`, `database/`, `config/hulagwai.php` | Backend (Laravel)                        | backend        |
| `ml-service/app/`                                     | Inference API + forensics + ensemble     | ML             |
| `ml-service/training/`                                | Colab training pipeline (.py + notebook) | ML             |
| `resources/js/api/`                                   | **Frontend API layer** (keep this)       | shared         |
| `resources/js/Pages`, `Layouts`, `Components`         | **Test UI only — replace freely**        | frontend team  |
| `docs/`                                               | API, security, datasets                  | everyone       |

---

## 1 · Run it locally (Windows + XAMPP)

**Requirements:** XAMPP (Apache + MySQL/MariaDB, PHP 8.2), Composer, Node 20+, Python 3.12–3.14.

```bash
# 1. PHP / JS dependencies
composer install
composer require barryvdh/laravel-dompdf      # PDF engine for reports (once)
npm install

# 2. Environment
copy .env.example .env
php artisan key:generate
```

Edit `.env`:

- start **MySQL** in XAMPP and create the DB: `CREATE DATABASE hulagwai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
- `DB_USERNAME` / `DB_PASSWORD` (XAMPP default: `root` / empty — fine locally, never in production)
- `ML_SERVICE_TOKEN` — generate one: `php -r "echo bin2hex(random_bytes(32));"`

```bash
php artisan migrate

# 3. ML service (Python venv)
cd ml-service
python -m venv .venv
# CPU build of PyTorch (smaller, no GPU needed) - then the rest:
.\.venv\Scripts\python.exe -m pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # paste the SAME ML_SERVICE_TOKEN here
cd ..

# 4. Start everything (web server + queue + scheduler + vite + ML service)
composer run dev
```

Open http://127.0.0.1:8000.

> **No trained model yet?** With `ML_ALLOW_METADATA_ONLY=true` (default in `ml-service/.env.example`) the service still runs the provenance check
> (it catches images that _declare_ their AI origin) and answers **Inconclusive** for everything else. Train the model (section 2) to get real predictions.

> **Python 3.14?** PyTorch publishes 3.14 wheels, but if `pip` cannot find a wheel for another dependency (timm, open_clip, safetensors…), create the venv with Python 3.12 instead.
> **8 GB RAM:** the default model (`ViT-B-16` + `convnext_tiny`) needs roughly 2 GB while running. Use `--clip-arch ViT-L-14` only on machines with 16 GB+.

Tests: `php artisan test` (backend, 16 tests) · `cd ml-service && pip install -r requirements-dev.txt && pytest` (ML service).

---

## 2 · Train the model on Google Colab (free GPU)

Your laptop's GPU (AMD Radeon 610M, integrated) cannot train deep models, so training runs on Colab; **the laptop only does inference on CPU**.

1. Get the code into Colab. Prefer the public clone cell in `ml-service/training/HulagwAI_Colab.ipynb`:
   ```bash
   git clone https://github.com/J0SH-ua/HulagwAI-ni-Arena.git /content/repo
   cd /content/repo/ml-service
   ```
   If the repository becomes private, create a GitHub token with read access and use `https://<TOKEN>@github.com/J0SH-ua/HulagwAI-ni-Arena.git`. Alternatively, zip `ml-service/` locally as `ml-service.zip`, upload it to Google Drive, and uncomment the upload option in the notebook.
2. Upload `ml-service/training/HulagwAI_Colab.ipynb` to Colab (`File ▸ Upload notebook`) or open it from GitHub.
3. In Colab, select `Runtime ▸ Change runtime type ▸ T4 GPU`.
4. Add Kaggle credentials: Kaggle ▸ *Settings ▸ API ▸ Create New Token*. In Colab's 🔑 **Secrets**, add `KAGGLE_USERNAME` and `KAGGLE_KEY`, then enable **Notebook access** for both.
5. Run the notebook cells from top to bottom. If `pip` installs the notebook dependencies, re-check that the runtime is using a T4 GPU before training.
6. Run the smoke test before the real model:
   ```bash
   python -m training.run_all --profile smoke --work /content/smoke --version 0.0.1
   ```
   This takes about 2–3 minutes and only proves that the pipeline runs; smoke-test metrics are meaningless.
7. Run the real training command. The estimate is 2–4 hours on a free T4, depending on Colab capacity:
   ```bash
   python -m training.run_all --profile colab_fast --work /content/drive/MyDrive/hulagwai_work --version 1.0.0 --with-ood
   ```
   Training artifacts and datasets are saved to Drive. Each stage skips completed output, so re-running the command after a disconnect continues the pipeline safely. Add `--genimage-root` or `--ood-real-dir` only when those optional dataset folders are available.
8. In the notebook, inspect the metrics and download the last `hulagwai-ensemble-<version>.zip` file. On Windows, extract the **contents of the archive** into `ml-service/models/current/`; the folder must contain `config.json`, `manifest.json`, `metrics.json`, and the `.safetensors` files directly. For example:
   ```powershell
   cd C:\Personal_Projects\HulagwAI-main
   Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\hulagwai-ensemble-1.0.0.zip" -DestinationPath .\ml-service\models\current -Force
   cd ml-service
   python -m app.verify
   ```
   If the ZIP creates an extra folder named `hulagwai-ensemble-1.0.0`, move that folder's contents up into `models/current/` before verification.
9. Restart the full local application:
   ```bash
   composer run dev
   ```
   Open `http://127.0.0.1:8000`. The PDF report and analysis endpoint now use the verified real model instead of metadata-only inference.

Prefer the command line directly in Colab? Use:

```bash
!python -m training.run_all --profile colab_fast --work /content/drive/MyDrive/hulagwai_work --version 1.0.0 --with-ood
```

The archive can also be verified from the repository root:
```bash
cd ml-service && python -m app.verify
```

Details, flags and troubleshooting: [`ml-service/training/README.md`](ml-service/training/README.md). Dataset links and licences: [`docs/DATASETS.md`](docs/DATASETS.md).

---

## 3 · How a decision is made

1. **Provenance check** (always): C2PA/JUMBF containers, IPTC `DigitalSourceType = trainedAlgorithmicMedia`, generator names in EXIF/XMP/PNG text chunks, Stable-Diffusion-WebUI `parameters`, ComfyUI graphs… A declared AI origin lifts the score to ≥ 98 %. _Absence of metadata proves nothing, and camera EXIF is reported but never lowers the score (it can be forged)._
2. **Three ML members**, each returning a logit:
    - **CLIP ViT + linear head** — generalises best to generators never seen in training;
    - **ConvNeXt** fine-tuned on native-resolution crops — catches low-level pixel artefacts;
    - **Frequency MLP** — spectrum / noise-residual statistics, independent of the other two.
      Images ≥ 224 px are inspected at **native resolution** (5 crops); resizing would erase the traces being looked for.
3. **Fusion**: logistic regression fitted on a validation split → probability `P(AI)`.
4. **Three-way verdict**: _Real_ ≤ `real_max`, _AI_ ≥ `ai_min`, otherwise **Inconclusive**. Thresholds are fitted so that decided calls reach ≥ 97 % precision on validation. The band widens automatically for tiny images or when the members disagree.

The confidence shown to users is _how strongly the model favours its prediction_ — not the probability the image is authentic. Every result says so.

## 4 · Privacy & storage rules

- **Guests** (not signed in): the image is analysed and the encrypted temporary copy is deleted immediately; only the result + a 480 px thumbnail stay in the encrypted server-side session (last 10, gone when the session ends). Nothing is kept in MySQL.
- **Signed-in users**: originals (≤ 5 MB each, ≤ 50 MB total) are stored **permanently, encrypted** (XChaCha20-Poly1305); filenames and result details are AES-256 encrypted columns. Users can delete one analysis, clear history, or delete the whole account (everything is erased).
- ⚠️ **Back up `APP_KEY`.** All encryption keys are derived from it; if it is lost, stored images and filenames cannot be decrypted. Decrypt manually with `php artisan hulagwai:decrypt <id> <outfile>`.

More: [`docs/SECURITY.md`](docs/SECURITY.md) (OWASP Top 10 mapping + production checklist) · [`docs/API.md`](docs/API.md) (endpoints for the frontend team).
