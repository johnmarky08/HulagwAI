"""The three ensemble members. Each returns ONE logit (positive = AI-generated).

clip  - frozen CLIP ViT image encoder + trained linear head ("UnivFD" idea: CLIP features generalise to
        generators never seen in training far better than a CNN trained end-to-end).
cnn   - ConvNeXt fine-tuned end-to-end on native-resolution crops (catches low-level pixel artefacts).
freq  - tiny MLP on spectrum / noise-residual statistics (independent, resolution-agnostic signal).

Weights are loaded with `safetensors` (no pickle -> no code execution from a tampered weight file).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from safetensors.numpy import load_file as load_np

from app import preprocess as P
from app.forensics import frequency


class ClipMember:
    name = "clip"
    role = "Semantic / generator-agnostic (CLIP ViT features)"

    def __init__(self, cfg: dict, root: Path, device: str = "cpu"):
        import open_clip
        import torch

        self.torch, self.device = torch, device
        self.size = int(cfg.get("crop", P.CROP))
        self.k = int(cfg.get("k_crops", 5))
        model, _, _ = open_clip.create_model_and_transforms(cfg["arch"], pretrained=cfg.get("pretrained", "openai"))
        self.encoder = model.eval().to(device)
        head = load_np(str(root / "clip_head.safetensors"))
        self.w = head["weight"].astype(np.float32).reshape(-1)
        self.b = float(head["bias"].reshape(-1)[0])

    def logit(self, img: Image.Image) -> float:
        t = self.torch
        x = t.from_numpy(P.crops_to_array(P.native_crops(img, self.size, self.k), P.CLIP_MEAN, P.CLIP_STD)).to(self.device)
        with t.inference_mode():
            f = self.encoder.encode_image(x)
            f = f / f.norm(dim=-1, keepdim=True)
        z = f.float().cpu().numpy() @ self.w + self.b
        return float(np.mean(z))


class CnnMember:
    name = "cnn"
    role = "Low-level pixel artefacts (ConvNeXt, native-resolution crops)"

    def __init__(self, cfg: dict, root: Path, device: str = "cpu"):
        import timm
        import torch
        from safetensors.torch import load_file

        self.torch, self.device = torch, device
        self.size = int(cfg.get("crop", P.CROP))
        self.k = int(cfg.get("k_crops", 5))
        net = timm.create_model(cfg["arch"], pretrained=False, num_classes=1)
        net.load_state_dict(load_file(str(root / "cnn.safetensors")))
        self.net = net.eval().to(device)

    def logit(self, img: Image.Image) -> float:
        t = self.torch
        x = t.from_numpy(P.crops_to_array(P.native_crops(img, self.size, self.k), P.IMAGENET_MEAN, P.IMAGENET_STD)).to(self.device)
        with t.inference_mode():
            z = self.net(x).reshape(-1)
        return float(z.float().mean())


class FreqMember:
    name = "frequency"
    role = "Spectrum & noise-residual statistics"

    def __init__(self, cfg: dict, root: Path, device: str = "cpu"):
        d = load_np(str(root / "freq_mlp.safetensors"))
        self.w1, self.b1, self.w2, self.b2 = (d[k].astype(np.float32) for k in ("w1", "b1", "w2", "b2"))
        self.mean, self.std = d["mean"].astype(np.float32), d["std"].astype(np.float32)
        if self.mean.shape[0] != frequency.N_FEATURES:
            raise ValueError("frequency head does not match the feature extractor version")

    def logit(self, img: Image.Image) -> float:
        x = (frequency.features(img) - self.mean) / (self.std + 1e-6)
        h = np.maximum(x @ self.w1 + self.b1, 0.0)
        return float(h @ self.w2.reshape(-1) + self.b2.reshape(-1)[0])


MEMBERS = {"clip": ClipMember, "cnn": CnnMember, "frequency": FreqMember}
