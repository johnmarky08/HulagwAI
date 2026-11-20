"""Evaluation metrics (numpy only, so they are unit-tested without torch). y: 1 = AI-generated, 0 = real."""
from __future__ import annotations

import numpy as np


def _arr(y, p):
    return np.asarray(y, dtype=np.int64), np.asarray(p, dtype=np.float64)


def _div(a: float, b: float) -> float:
    return float(a / b) if b else float("nan")


def confusion(y, p, threshold: float = 0.5) -> dict[str, int]:
    y, p = _arr(y, p)
    pred = p >= threshold
    return {"tn": int(((y == 0) & ~pred).sum()), "fp": int(((y == 0) & pred).sum()),
            "fn": int(((y == 1) & ~pred).sum()), "tp": int(((y == 1) & pred).sum())}


def roc_auc(y, p) -> float:
    y, p = _arr(y, p)
    n1, n0 = int((y == 1).sum()), int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    sp = p[order]
    i = 0
    while i < len(sp):                      # average ranks for ties
        j = i
        while j + 1 < len(sp) and sp[j + 1] == sp[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def average_precision(y, p) -> float:
    """Step-wise AP over distinct thresholds (same definition as scikit-learn)."""
    y, p = _arr(y, p)
    if (y == 1).sum() == 0:
        return float("nan")
    order = np.argsort(-p, kind="mergesort")
    ys, ps = y[order], p[order]
    last = np.r_[np.where(np.diff(ps))[0], len(ps) - 1]      # last index of each distinct score
    tp = np.cumsum(ys)[last]
    prec = tp / (last + 1)
    rec = tp / ys.sum()
    return float(np.sum(np.diff(np.r_[0.0, rec]) * prec))


def ece(y, p, bins: int = 10) -> float:
    """Expected calibration error of P(AI)."""
    y, p = _arr(y, p)
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(total)


def binary_report(y, p, threshold: float = 0.5) -> dict[str, float | int]:
    y, p = _arr(y, p)
    c = confusion(y, p, threshold)
    tn, fp, fn, tp = c["tn"], c["fp"], c["fn"], c["tp"]
    recall, spec = _div(tp, tp + fn), _div(tn, tn + fp)
    prec = _div(tp, tp + fp)
    eps = 1e-12
    pc = np.clip(p, eps, 1 - eps)
    mcc_den = np.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {
        "n": int(len(y)), "threshold": threshold,
        "accuracy": _div(tp + tn, len(y)), "precision": prec, "recall": recall, "specificity": spec,
        "f1": _div(2 * prec * recall, prec + recall) if prec == prec and recall == recall else float("nan"),
        "balanced_accuracy": (recall + spec) / 2 if recall == recall and spec == spec else float("nan"),
        "mcc": float((tp * tn - fp * fn) / mcc_den) if mcc_den else float("nan"),
        "fpr": _div(fp, fp + tn), "fnr": _div(fn, fn + tp), "npv": _div(tn, tn + fn),
        "roc_auc": roc_auc(y, p), "average_precision": average_precision(y, p),
        "mae": float(np.abs(p - y).mean()), "mse": float(((p - y) ** 2).mean()),
        "rmse": float(np.sqrt(((p - y) ** 2).mean())), "brier": float(((p - y) ** 2).mean()),
        "log_loss": float(-(y * np.log(pc) + (1 - y) * np.log(1 - pc)).mean()),
        "ece": ece(y, p), "confusion": c,
    }


def selective_report(y, p, real_max: float, ai_min: float) -> dict[str, float]:
    """Behaviour of the 3-way verdict: how often we commit, and how right we are when we do."""
    y, p = _arr(y, p)
    decided = (p <= real_max) | (p >= ai_min)
    pred = (p >= ai_min).astype(int)
    acc = float((pred[decided] == y[decided]).mean()) if decided.any() else float("nan")
    return {"coverage": float(decided.mean()), "inconclusive_rate": float(1 - decided.mean()), "accuracy_decided": acc,
            "real_max": real_max, "ai_min": ai_min}


def roc_curve(y, p, max_points: int = 60) -> dict[str, list[float]]:
    """ROC points (fpr, tpr) down-sampled for plotting."""
    y, p = _arr(y, p)
    order = np.argsort(-p, kind="mergesort")
    ys, ps = y[order], p[order]
    last = np.r_[np.where(np.diff(ps))[0], len(ps) - 1]
    tp, fp = np.cumsum(ys)[last], (last + 1) - np.cumsum(ys)[last]
    tpr = np.r_[0.0, tp / max(1, ys.sum())]
    fpr = np.r_[0.0, fp / max(1, (1 - ys).sum())]
    if len(fpr) > max_points:
        keep = np.unique(np.linspace(0, len(fpr) - 1, max_points).astype(int))
        fpr, tpr = fpr[keep], tpr[keep]
    return {"fpr": [round(float(v), 5) for v in fpr], "tpr": [round(float(v), 5) for v in tpr]}


def calibration_bins(y, p, bins: int = 10) -> list[dict]:
    """Reliability diagram data: predicted P(AI) vs observed share of AI images."""
    y, p = _arr(y, p)
    idx = np.clip((p * bins).astype(int), 0, bins - 1)
    out = []
    for b in range(bins):
        m = idx == b
        out.append({"bin": f"{b / bins:.1f}-{(b + 1) / bins:.1f}", "n": int(m.sum()),
                    "mean_p": float(p[m].mean()) if m.any() else None, "frac_ai": float(y[m].mean()) if m.any() else None})
    return out


def clean(obj):
    """NaN/inf -> None so the report is valid JSON."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, float) and not np.isfinite(obj):
        return None
    return obj
