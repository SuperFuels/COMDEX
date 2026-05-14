# backend/symatics/operators/helpers.py
from __future__ import annotations
import math
from typing import Optional, Tuple


def _merge_meta(a: Optional[dict], b: Optional[dict], extra: Optional[dict] = None) -> dict:
    """
    Merge metadata dicts:
    - a first, then b overrides, then extra overrides all.
    """
    m: dict = {}
    if isinstance(a, dict):
        m.update(a)
    if isinstance(b, dict):
        m.update(b)
    if isinstance(extra, dict):
        m.update(extra)
    return m

def _pol_blend(pa: str, pb: str) -> str:
    """
    Simple polarization blending rule (v0.1):
    - identical -> keep
    - H/V vs circular -> prefer existing pa
    - H vs V mismatch -> keep pa (stable bias)
    """
    if pa == pb:
        return pa
    return pa  # gentle bias toward first operand


def _complex_from_amp_phase(A: float, phi: float) -> complex:
    return complex(A * math.cos(phi), A * math.sin(phi))


def _amp_phase_from_complex(z: complex) -> Tuple[float, float]:
    A = abs(z)
    phi = (math.atan2(z.imag, z.real) + math.tau) % math.tau
    return A, phi


def _freq_blend(fa: float, fb: float) -> float:
    """
    Frequency blending (v0.1):
    - If nearly equal -> average
    - Else prefer closer to dominant
    """
    if abs(fa - fb) < 1e-9:
        return (fa + fb) / 2.0
    return fa if abs(fa - fb) < abs(fb - fa) else fb