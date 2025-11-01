# ===============================
# 📁 backend/quant/qmath/qmath_waveops.py
# ===============================
"""
🌊 QMathWaveOps - Core Wave-Math Primitives for Q-Series
--------------------------------------------------------
Implements symbolic and numeric operators aligned with
Symatics Algebra v0.1:

    ⊕  Superposition     (additive interference)
    ↔  Entanglement      (state correlation)
    ⟲  Resonance         (feedback amplification)
    ∇  Collapse          (measurement / projection)
    μ  Measurement       (expectation value)
    π  Projection        (state extraction)

Used by QPy and QQC for unified wave computation.
"""

from __future__ import annotations
import cmath
import math
import random
from typing import Any, Dict, List, Tuple


# ----------------------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------------------
def clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def normalize_phase(angle: float) -> float:
    """Normalize an angle to [-π, π]."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


# ----------------------------------------------------------------------
# ⊕ Superposition
# ----------------------------------------------------------------------
def superpose(a: complex, b: complex, weight: float = 0.5) -> complex:
    """
    Weighted superposition of two wave states.
    """
    w1, w2 = weight, 1.0 - weight
    return (w1 * a) + (w2 * b)


# ----------------------------------------------------------------------
# ↔ Entanglement
# ----------------------------------------------------------------------
def entangle(a: complex, b: complex) -> Tuple[complex, complex, float]:
    """
    Compute entanglement correlation coefficient between two waves.
    Returns (a′, b′, ρ) where ρ ∈ [0, 1].
    """
    ρ = clamp(abs((a.conjugate() * b).real))
    phase_avg = (cmath.phase(a) + cmath.phase(b)) / 2.0
    shift = cmath.exp(1j * phase_avg)
    return a * shift, b * shift, ρ


# ----------------------------------------------------------------------
# ⟲ Resonance
# ----------------------------------------------------------------------
def resonate(a: complex, feedback: float = 0.1, damping: float = 0.95, steps: int = 5) -> complex:
    """
    Iteratively reinforce amplitude and phase alignment.
    """
    ψ = a
    for _ in range(steps):
        ψ = (1 + feedback) * ψ * damping
    return ψ


# ----------------------------------------------------------------------
# ∇ Collapse and μ Measurement
# ----------------------------------------------------------------------
def collapse(a: complex) -> float:
    """
    Collapse a wave to measurable intensity (|ψ|2).
    """
    return abs(a) ** 2


def measure(a: complex) -> Dict[str, Any]:
    """
    Return a dictionary of observable quantities.
    """
    return {
        "amplitude": abs(a),
        "phase": normalize_phase(cmath.phase(a)),
        "intensity": abs(a) ** 2,
    }


# ----------------------------------------------------------------------
# π Projection
# ----------------------------------------------------------------------
def project(a: complex, axis_phase: float = 0.0) -> complex:
    """
    Project a wave onto a reference phase axis.
    """
    phase = normalize_phase(cmath.phase(a) - axis_phase)
    return abs(a) * cmath.exp(1j * phase)


# ----------------------------------------------------------------------
# High-level composite operation
# ----------------------------------------------------------------------
def interact(a: complex, b: complex) -> Dict[str, Any]:
    """
    Full symbolic wave interaction pipeline:
      ⊕ -> ↔ -> ⟲ -> ∇ -> μ
    """
    s = superpose(a, b)
    ea, eb, ρ = entangle(s, b)
    r = resonate(ea)
    I = collapse(r)
    μ = measure(r)
    return {
        "superposed": s,
        "entangled_a": ea,
        "entangled_b": eb,
        "correlation": ρ,
        "resonant": r,
        "intensity": I,
        "measurement": μ,
    }


# ----------------------------------------------------------------------
# Self-test / demo
# ----------------------------------------------------------------------
if __name__ == "__main__":
    a = cmath.exp(1j * 0.3)
    b = cmath.exp(1j * 1.0)
    out = interact(a, b)
    for k, v in out.items():
        print(f"{k:>14}: {v}")