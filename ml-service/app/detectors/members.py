"""The three ensemble members. Each returns ONE logit (positive = AI-generated).

clip  - frozen CLIP ViT image encoder + trained linear head ("UnivFD" idea: CLIP features generalise to
        generators never seen in training far better than a CNN trained end-to-end).
cnn   - ConvNeXt fine-tuned end-to-end on native-resolution crops (catches low-level pixel artefacts).
freq  - tiny MLP on spectrum / noise-residual statistics (independent, resolution-agnostic signal).

`analyze()` returns (logit, embedding) from ONE forward pass; the embeddings of clip and cnn also feed the
generator-attribution head, so "which AI made this?" costs no extra model. Weights are loaded with
`safetensors` (no pickle -> no code execution from a tampered weight file).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from safetensors.numpy import load_file as load_np

from app import preprocess as P
from app.forensics import frequency


def _unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-12)


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

    def analyze(self, img: Image.Image) -> tuple[float, np.ndarray]:
        t = self.torch
        x = t.from_numpy(P.crops_to_array(P.native_crops(img, self.size, self.k), P.CLIP_MEAN, P.CLIP_STD)).to(self.device)
        with t.inference_mode():
            f = self.encoder.encode_image(x)
            f = f / f.norm(dim=-1, keepdim=True)
        fn = f.float().cpu().numpy()
        return float(np.mean(fn @ self.w + self.b)), _unit(fn.mean(0))

    def logit(self, img: Image.Image) -> float:
        return self.analyze(img)[0]


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

    def _forward(self, crops: list[Image.Image]) -> tuple[np.ndarray, np.ndarray]:
        t = self.torch
        x = t.from_numpy(P.crops_to_array(crops, P.IMAGENET_MEAN, P.IMAGENET_STD)).to(self.device)
        with t.inference_mode():
            fmap = self.net.forward_features(x)
            logits = self.net.forward_head(fmap).reshape(-1)
            pooled = self.net.forward_head(fmap, pre_logits=True)
        return logits.float().cpu().numpy(), pooled.float().cpu().numpy()

    def analyze(self, img: Image.Image) -> tuple[float, np.ndarray]:
        z, pooled = self._forward(P.native_crops(img, self.size, self.k))
        return float(z.mean()), _unit(pooled.mean(0))

    def logit(self, img: Image.Image) -> float:
        return self.analyze(img)[0]

    def patch_logits(self, crops: list[Image.Image]) -> np.ndarray:
        """One logit per crop (used for the suspicious-region heat map)."""
        return self._forward(crops)[0]


class FreqMember:
    name = "frequency"
    role = "Spectrum & noise-residual statistics"

    def __init__(self, cfg: dict, root: Path, device: str = "cpu"):
        d = load_np(str(root / "freq_mlp.safetensors"))
        self.w1, self.b1, self.w2, self.b2 = (d[k].astype(np.float32) for k in ("w1", "b1", "w2", "b2"))
        self.mean, self.std = d["mean"].astype(np.float32), d["std"].astype(np.float32)
        if self.mean.shape[0] != frequency.N_FEATURES:
            raise ValueError("frequency head does not match the feature extractor version")

    def analyze(self, img: Image.Image) -> tuple[float, None]:
        x = (frequency.features(img) - self.mean) / (self.std + 1e-6)
        h = np.maximum(x @ self.w1 + self.b1, 0.0)
        return float(h @ self.w2.reshape(-1) + self.b2.reshape(-1)[0]), None

    def logit(self, img: Image.Image) -> float:
        return self.analyze(img)[0]


MEMBERS = {"clip": ClipMember, "cnn": CnnMember, "frequency": FreqMember}
