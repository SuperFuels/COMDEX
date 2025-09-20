from __future__ import annotations
from typing import Tuple
from math import pi
from .signature import Signature

def _phase_diff(a: float, b: float) -> float:
    d = abs((a - b) % (2*pi))
    return min(d, 2*pi - d)

def distance(a: Signature, b: Signature, w=(1.0,1.0,1.0)) -> float:
    """Weighted distance over (amplitude, frequency, phase)."""
    return (
        w[0]*abs(a.amplitude - b.amplitude) +
        w[1]*abs(a.frequency - b.frequency) +
        w[2]*_phase_diff(a.phase, b.phase)
    )