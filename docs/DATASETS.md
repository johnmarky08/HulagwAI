# Datasets

Always read each dataset's own licence/terms before redistributing models or data. Links below were checked while preparing this project.

| Dataset | Used for | Link |
|---|---|---|
| **CIFAKE** — 60 k real (CIFAR-10) + 60 k Stable-Diffusion-1.4 images, 32×32 | baseline training + test | https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images |
| **ArtiFact** — 2.5 M images, 25 generators (GANs + diffusion), JPEG-compressed/cropped variants | training + test | https://github.com/awsaf49/artifact · paper: https://arxiv.org/abs/2302.11970 · Kaggle id `awsaf49/artifact-dataset` |
| **GenImage** — million-scale benchmark (Midjourney, SD 1.4/1.5, Wukong, ADM, BigGAN, GLIDE, VQDM) vs ImageNet | training + test (subset) | paper: https://arxiv.org/abs/2306.08571 · repo mirror: https://github.com/weili-thu/genimage |
| **OpenFake** — ≈3 M real + ≈963 k synthetic images; every synthetic image has a `model` field (DALL·E 3, Midjourney v6/v7, GPT Image, Imagen 3/4, Ideogram, Grok-2, FLUX variants, SD 1.4–3.5 …), CC-BY-NC-4.0 (config `core`) | detection **and generator attribution** (streamed subset) | https://huggingface.co/datasets/ComplexDataLab/OpenFake · paper: https://arxiv.org/abs/2509.09495 |
| **Synthbuster** — DALL·E 2/3, Firefly, Midjourney v5, SD variants | **unseen-generator test only** | https://zenodo.org/records/10066460 |
| RAISE (optional real camera photos for the Synthbuster test) — distributed as a **CSV of download links** (`RAISE_1k.csv`, `RAISE_2k.csv` …); pass it with `--raise-csv` and a capped sample of its TIFFs is downloaded | OOD real images | http://loki.disi.unitn.it/RAISE/download.html |
| Community Forensics (optional, thousands of generators incl. FLUX) | optional extra | paper: https://arxiv.org/abs/2411.04125 · project: https://jespark.net/projects/2024/community_forensics |

## Datasets considered for "why it looks AI" but NOT used
| Dataset | Why not |
|---|---|
| FakeClue — https://huggingface.co/datasets/lingcco/FakeClue · https://arxiv.org/abs/2503.14905 | Text explanations of artefacts, but they were produced by aggregating several AI models and contain errors; using them needs a ~7B vision-language model that does not fit an 8 GB CPU laptop. |
| Holmes-Set — https://arxiv.org/abs/2507.02664 | Explanation annotations, but no verified download link was found. |

Because of this, HulagwAI's "why it looks AI" section is **grounded evidence only** (detector signals, provenance, a heat map) and never claims specific defects such as extra fingers.

## Data card (what the guideline asks to describe)
| | CIFAKE | ArtiFact | GenImage | Synthbuster |
|---|---|---|---|---|
| **Attributes** | RGB image, 32×32 PNG/JPG | RGB image + `metadata.csv` (path, label, category) | RGB image, folder-structured per generator | RGB image, folder per generator |
| **Target** | REAL (CIFAR-10) = 0, FAKE (Stable Diffusion 1.4) = 1 | real = 0, synthetic = 1 | `nature` = 0, `ai` = 1 | all fake = 1 (reals from RAISE optional, `--raise-csv`) |
| **Size** | 120 000 images (100 000 train / 20 000 test) | ≈ 2.5 M images | > 1 M pairs (subset used) | ≈ 9 000 images |
| **Known limitations** | tiny, one generator, CIFAR-10 object classes only | very large; JPEG/crop variants; near-duplicate reals possible across splits | real = JPEG vs fake = PNG shortcut; hosted on Drive/Baidu | small; test-only |
| **Role here** | train + test | train + test | train + test (subset) | unseen-generator test |

Exact image counts per split used in *your* run are written to `datasets.json` and the model card. Check each dataset's licence page before redistributing the data inside the submission ZIP; if redistribution is not allowed, submit only the links above plus `training/README.md` (the guideline allows this).

## Generator families (attribution)
Raw generator names are mapped to families in `ml-service/app/attribution.py::family_of` (e.g. `sd-1.5` → Stable Diffusion, `sdxl-turbo` → SDXL/SD3, `flux-1.1-pro` → FLUX, `dall-e-3` → DALL·E, `gpt-image-1` → GPT Image, `imagen-4`/`nano-banana` → Google, `stylegan2` → GAN, others → *Other AI*). CIFAKE is excluded from attribution training because all its images are 32×32. A family with fewer than 60 training images is dropped and reported in the model card. You can add your own generator-labelled images with `--generator-root <folder>/<generator-name>/*.png` (+ a `real/` folder).

## Practical notes
* **CIFAKE is 32×32.** A model trained *only* on it will not generalise to real photos or to Midjourney/DALL·E/FLUX output. That is why the pipeline mixes datasets and keeps Synthbuster for an honest unseen-generator test.
* **ArtiFact is large (tens of GB), but only what is used is downloaded:** stage 1 fetches its metadata.csv files and the sampled images one by one (kagglehub >= 1.0) into `<work>/artifact` on Drive, so they survive a new Colab runtime. `--artifact-root` still works for an already-extracted copy.
* **GenImage** is hosted on Google Drive / Baidu (see its repo). Download the generators you want (a few is fine), keep the original layout `<generator>/{train,val}/{ai,nature}/…`, put them on Drive and pass `--genimage-root`.
* Known dataset bias: in GenImage the real images are JPEG and the fakes PNG. The training pipeline applies the same random JPEG/blur/resize to both classes so the model cannot cheat on file format.
* The ArtiFact / GenImage / Synthbuster adapters (`training/data_sources.py`) were written from the public documentation without downloading the data. They validate what they find and stop with a clear message if the layout differs — if that happens, adjust the few lines in the adapter.
* Missing coverage: no public dataset contains every current generator. Expect weaker results on the newest models (FLUX, Midjourney v7, GPT-image…). Provide extra data (e.g. Community Forensics, or your own labelled images) and re-run training to improve this.
