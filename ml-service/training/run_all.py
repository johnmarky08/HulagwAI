"""Run the whole pipeline:  python -m training.run_all --profile colab_fast --work /content/drive/MyDrive/hulagwai --with-ood

Free Colab (~2.5 h GPU limit)?  --profile colab_mini, or shrink any profile with --subset 0.25 (fraction of the
data) and/or --cnn-epochs 1. Use a separate --work folder per data size.

Each stage skips itself if its output already exists, so you can simply re-run after a Colab disconnect.

No GPU (e.g. Colab's free GPU quota is used up)? Only the stages that do not need one run - 01 (all downloads, the
longest wait) and 05 (frequency model, CPU-only anyway). Their results are saved in --work, so the next run on a GPU
starts directly with the GPU stages. Training the CNN / extracting CLIP features on Colab's 2 CPU cores would take
days and be cut off by the ~12 h session limit, losing the work. Pass --allow-cpu to force a full CPU run anyway.
"""
import subprocess
import sys

STAGES = ["01_prepare_data", "02_extract_clip_features", "03_train_clip_head", "03b_cross_validate", "04_train_cnn", "05_train_frequency",
          "06_fit_fusion", "06b_train_attribution", "07_evaluate", "08_export_bundle"]
CPU_STAGES = ["01_prepare_data", "05_train_frequency"]


def has_gpu() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001
        return False


def profile_of(argv: list[str]) -> str:
    for i, a in enumerate(argv):
        if a == "--profile" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--profile="):
            return a.split("=", 1)[1]
    return "colab_fast"


def main() -> None:
    argv = sys.argv[1:]
    allow_cpu = "--allow-cpu" in argv
    argv = [a for a in argv if a != "--allow-cpu"]          # the stages do not know this flag
    stages = STAGES
    cpu_only = not has_gpu() and profile_of(argv) != "smoke" and not allow_cpu
    if cpu_only:
        stages = CPU_STAGES
        print("\n" + "!" * 100 +
              "\nNO GPU FOUND - running only the stages that do not need one: " + ", ".join(stages) +
              "\n(downloads + frequency model; results are saved in --work). When a GPU is available again, switch the"
              "\nruntime to T4 GPU and run the SAME command: finished stages are skipped and training continues."
              "\n" + "!" * 100, flush=True)
    for s in stages:
        print(f"\n===== {s} =====", flush=True)
        r = subprocess.run([sys.executable, "-m", f"training.{s}", *argv])
        if r.returncode:
            sys.exit(f"stage {s} failed (exit {r.returncode})")
    if cpu_only:
        print("\nCPU part finished. Remaining (needs a GPU): " + ", ".join(x for x in STAGES if x not in CPU_STAGES), flush=True)


if __name__ == "__main__":
    main()
