"""Ensemble fusion + three-way decision (real / ai_generated / inconclusive). Pure numpy -> unit-testable."""
from __future__ import annotations

import math
from typing import Any

# "Inconclusive" only for a true 50/50: the AI score rounds to 50 %. Everything else gets a Real / AI call.
INCONCLUSIVE_BAND = (0.495, 0.505)   # real if p < 0.495, ai_generated if p >= 0.505
DEFAULT_THRESHOLDS = {"real_max": INCONCLUSIVE_BAND[0], "ai_min": INCONCLUSIVE_BAND[1], "disagreement_max": 0.45}


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def fuse(logits: dict[str, float], fusion_cfg: dict[str, Any]) -> dict[str, Any]:
    members = fusion_cfg["members"]
    weights = fusion_cfg["weights"]
    z = float(fusion_cfg.get("bias", 0.0)) + sum(w * logits[m] for m, w in zip(members, weights))
    probs = [sigmoid(logits[m]) for m in members]
    mean = sum(probs) / len(probs)
    disagreement = math.sqrt(sum((p - mean) ** 2 for p in probs) / len(probs))
    return {"p": sigmoid(z), "disagreement": disagreement, "member_p": dict(zip(members, probs))}


def decide(p: float, disagreement: float, thresholds: dict[str, float], min_side: int, strong_provenance: bool) -> dict[str, Any]:
    # Trained thresholds are intentionally ignored: the band is fixed to a genuine 50/50. Low resolution and member
    # disagreement are still surfaced as warnings/evidence, but no longer turn a lean into "Inconclusive".
    lo, hi = INCONCLUSIVE_BAND
    widened: list[str] = []
    source = "model"
    if strong_provenance:
        # The file itself declares AI origin. Never *lower* the score; lift it to a high floor.
        p, source = max(p, 0.98), "provenance"
    verdict = "ai_generated" if p >= hi else "real" if p < lo else "inconclusive"
    confidence = p if verdict == "ai_generated" else (1 - p) if verdict == "real" else max(p, 1 - p)
    return {"verdict": verdict, "p": p, "confidence": confidence, "source": source,
            "bands": {"real_max": round(lo, 4), "ai_min": round(hi, 4)}, "widened_by": widened}
