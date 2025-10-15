# -*- coding: utf-8 -*-
"""
📈 coherence_metrics.py – Phase Drift, Entropy, and Visibility Computation
Part of Tessaris Symatics Lightwave Engine (SLE v0.5+)

Purpose:
    Provides low-level quantitative metrics used for SQI scoring and
    adaptive feedback gating (Δφ, entropy, visibility).

Inputs:
    - Phase samples (radians)
    - Amplitude samples or intensity stream
    - Coherence values (0–1)

Outputs:
    - Phase drift Δφ
    - Entropy H (Shannon-style, normalized)
    - Visibility V = (Imax − Imin) / (Imax + Imin)
"""

import numpy as np
import math
from typing import List, Dict


# ===============================================================
# Phase Drift Δφ
# ===============================================================
def phase_drift(phases: List[float]) -> float:
    """
    Compute mean absolute phase drift (Δφ) across samples.
    Returns value in radians (0–π).
    """
    if len(phases) < 2:
        return 0.0
    diffs = np.diff(np.unwrap(phases))
    return float(np.mean(np.abs(diffs)))


# ===============================================================
# Wave Entropy (Amplitude Distribution)
# ===============================================================
def wave_entropy(amplitudes: List[float]) -> float:
    """
    Compute normalized entropy of amplitude distribution.
    Returns 0.0–1.0 range, where 0 = ordered, 1 = chaotic.
    """
    if not amplitudes:
        return 0.0
    amps = np.abs(amplitudes)
    p = amps / np.sum(amps) if np.sum(amps) > 0 else np.zeros_like(amps)
    entropy = -np.sum([pi * math.log(pi + 1e-12) for pi in p])
    max_entropy = math.log(len(p)) if len(p) > 1 else 1.0
    return float(min(entropy / max_entropy, 1.0))


# ===============================================================
# Visibility Index
# ===============================================================
def visibility_index(intensities: List[float]) -> float:
    """
    Compute classical fringe visibility metric:
        V = (Imax − Imin) / (Imax + Imin)
    Returns 0.0–1.0 (0 = dark/no contrast, 1 = high coherence).
    """
    if not intensities:
        return 0.0
    Imax = np.max(intensities)
    Imin = np.min(intensities)
    denom = Imax + Imin
    return float((Imax - Imin) / denom) if denom > 0 else 0.0


# ===============================================================
# Composite SQI Metric (optional convenience)
# ===============================================================
def sqi_composite(phases: List[float], amplitudes: List[float]) -> Dict[str, float]:
    """
    Combine Δφ, entropy, and visibility into an SQI-ready metric set.
    """
    drift = phase_drift(phases)
    entropy = wave_entropy(amplitudes)
    intensity = [a**2 for a in amplitudes]
    visibility = visibility_index(intensity)

    # Invert entropy for coherence (lower entropy = higher SQI)
    coherence_factor = max(0.0, 1.0 - entropy)
    sqi = round(coherence_factor * visibility * math.exp(-drift), 3)

    return {
        "phase_drift": round(drift, 4),
        "entropy": round(entropy, 4),
        "visibility": round(visibility, 4),
        "sqi_score": sqi,
    }