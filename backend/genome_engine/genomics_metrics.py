from __future__ import annotations
from typing import Dict, List
import math

def cosine(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(len(a)):
        dot += a[i] * b[i]
        na += a[i] * a[i]
        nb += b[i] * b[i]
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)

def _onehot_flat(tokens: List[int], vocab: int = 4) -> List[float]:
    out = [0.0] * (vocab * len(tokens))
    for i, t in enumerate(tokens):
        tt = int(t)
        if 0 <= tt < vocab:
            out[vocab * i + tt] = 1.0
    return out

def rho_from_tokens(tx: List[int], rx: List[int]) -> float:
    if not tx or len(tx) != len(rx):
        return 0.0
    return cosine(_onehot_flat(tx), _onehot_flat(rx))

def crosstalk_matrix(streams: List[List[int]]) -> List[List[float]]:
    k = len(streams)
    out = [[0.0 for _ in range(k)] for _ in range(k)]
    if k == 0:
        return out
    flats = [_onehot_flat(s) for s in streams]
    for i in range(k):
        for j in range(k):
            out[i][j] = cosine(flats[i], flats[j])
    return out

def drift_mean(rho_trace: List[float], warmup: int) -> float:
    if len(rho_trace) < 2:
        return 0.0
    start = max(0, int(warmup))
    xs = rho_trace[start:]
    if len(xs) < 2:
        return 0.0
    s = 0.0
    for i in range(1, len(xs)):
        s += abs(xs[i] - xs[i - 1])
    return s / (len(xs) - 1)

def checks(thresholds: Dict, summary: Dict) -> List[Dict]:
    out: List[Dict] = []

    def add_ge(cid: str, value: float, thr: float):
        out.append({
            "id": cid,
            "pass": bool(value >= thr),
            "value": float(value),
            "threshold": float(thr),
            "margin": float(value - thr),
        })

    def add_le(cid: str, value: float, thr: float):
        out.append({
            "id": cid,
            "pass": bool(value <= thr),
            "value": float(value),
            "threshold": float(thr),
            "margin": float(thr - value),
        })

    if "rho_matched" in summary:
        add_ge("GX1_RHO_MATCHED_MIN",
               float(summary["rho_matched"]),
               float(thresholds.get("rho_matched_min", 0.80)))

    if "rho_mismatch" in summary:
        add_le("GX1_RHO_MISMATCH_ABS_MAX",
               abs(float(summary["rho_mismatch"])),
               float(thresholds.get("rho_mismatch_abs_max", 0.20)))

    if "crosstalk_max" in summary:
        add_le("GX1_CROSSTALK_MAX",
               float(summary["crosstalk_max"]),
               float(thresholds.get("crosstalk_max", 0.20)))

    if "coherence_mean" in summary:
        add_ge("GX1_COHERENCE_MEAN_MIN",
               float(summary["coherence_mean"]),
               float(thresholds.get("coherence_mean_min", 0.80)))

    if "drift_mean" in summary:
        add_le("GX1_DRIFT_MEAN_MAX",
               float(summary["drift_mean"]),
               float(thresholds.get("drift_mean_max", 0.08)))

    return out
