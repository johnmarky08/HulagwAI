"""Run the whole pipeline:  python -m training.run_all --profile colab_fast --work /content/drive/MyDrive/hulagwai --with-ood

Each stage skips itself if its output already exists, so you can simply re-run after a Colab disconnect.
"""
import subprocess
import sys

STAGES = ["01_prepare_data", "02_extract_clip_features", "03_train_clip_head", "04_train_cnn", "05_train_frequency",
          "06_fit_fusion", "07_evaluate", "08_export_bundle"]


def main() -> None:
    for s in STAGES:
        print(f"\n===== {s} =====", flush=True)
        r = subprocess.run([sys.executable, "-m", f"training.{s}", *sys.argv[1:]])
        if r.returncode:
            sys.exit(f"stage {s} failed (exit {r.returncode})")


if __name__ == "__main__":
    main()
