# Datasets

Always read each dataset's own licence/terms before redistributing models or data. Links below were checked while preparing this project.

| Dataset | Used for | Link |
|---|---|---|
| **CIFAKE** — 60 k real (CIFAR-10) + 60 k Stable-Diffusion-1.4 images, 32×32 | baseline training + test | https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images |
| **ArtiFact** — 2.5 M images, 25 generators (GANs + diffusion), JPEG-compressed/cropped variants | training + test | https://github.com/awsaf49/artifact · paper: https://arxiv.org/abs/2302.11970 · Kaggle id `awsaf49/artifact-dataset` |
| **GenImage** — million-scale benchmark (Midjourney, SD 1.4/1.5, Wukong, ADM, BigGAN, GLIDE, VQDM) vs ImageNet | training + test (subset) | paper: https://arxiv.org/abs/2306.08571 · repo mirror: https://github.com/weili-thu/genimage |
| **Synthbuster** — DALL·E 2/3, Firefly, Midjourney v5, SD variants | **unseen-generator test only** | https://zenodo.org/records/10066460 |
| RAISE-1k (optional real photos for the Synthbuster test) | OOD real images | http://loki.disi.unitn.it/RAISE/download.html |
| Community Forensics (optional, thousands of generators incl. FLUX) | optional extra | paper: https://arxiv.org/abs/2411.04125 · project: https://jespark.net/projects/2024/community_forensics |

## Practical notes
* **CIFAKE is 32×32.** A model trained *only* on it will not generalise to real photos or to Midjourney/DALL·E/FLUX output. That is why the pipeline mixes datasets and keeps Synthbuster for an honest unseen-generator test.
* **ArtiFact is large (tens of GB).** On Colab pass `--artifact-root` if you already have it on Drive, or lower `artifact_per_class` in `training/common.py`.
* **GenImage** is hosted on Google Drive / Baidu (see its repo). Download the generators you want (a few is fine), keep the original layout `<generator>/{train,val}/{ai,nature}/…`, put them on Drive and pass `--genimage-root`.
* Known dataset bias: in GenImage the real images are JPEG and the fakes PNG. The training pipeline applies the same random JPEG/blur/resize to both classes so the model cannot cheat on file format.
* The ArtiFact / GenImage / Synthbuster adapters (`training/data_sources.py`) were written from the public documentation without downloading the data. They validate what they find and stop with a clear message if the layout differs — if that happens, adjust the few lines in the adapter.
* Missing coverage: no public dataset contains every current generator. Expect weaker results on the newest models (FLUX, Midjourney v7, GPT-image…). Provide extra data (e.g. Community Forensics, or your own labelled images) and re-run training to improve this.
