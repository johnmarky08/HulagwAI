"""Ensemble fusion + three-way decision (real / ai_generated / inconclusive). Pure numpy -> unit-testable."""
from __future__ import annotations

import math
from typing import Any

DEFAULT_THRESHOLDS = {"real_max": 0.40, "ai_min": 0.60, "disagreement_max": 0.35}


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
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    lo, hi = t["real_max"], t["ai_min"]
    widened: list[str] = []
    if min_side < 64:                      # tiny images carry little evidence -> wider "inconclusive" band
        lo, hi = lo - 0.05, hi + 0.05
        widened.append("low_resolution")
    if disagreement > t["disagreement_max"]:  # members contradict each other -> be modest
        lo, hi = lo - 0.10, hi + 0.10
        widened.append("members_disagree")

    source = "model"
    if strong_provenance:
        # The file itself declares AI origin. Never *lower* the score; lift it to a high floor.
        p, source = max(p, 0.98), "provenance"
    verdict = "ai_generated" if p >= hi else "real" if p <= lo else "inconclusive"
    confidence = p if verdict == "ai_generated" else (1 - p) if verdict == "real" else max(p, 1 - p)
    return {"verdict": verdict, "p": p, "confidence": confidence, "source": source,
            "bands": {"real_max": round(lo, 4), "ai_min": round(hi, 4)}, "widened_by": widened}
