# backend/modules/aion_resonance/semantic_estimator.py
"""
Lightweight semantic estimation for glyph encoding.

Outputs:
  ρ  (resonance)
  Ī  (intensity / clarity)
  SQI (Symbolic Quality Index)

Note: initial heuristics — will evolve with HQCE feedback.
"""

import math
import hashlib

def _scalar(text: str) -> float:
    """Stable hash → 0..1 scalar for deterministic pseudo-signal."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF

def estimate_resonance(text: str) -> float:
    """Semantic resonance ~ meaningful coherence."""
    base = _scalar(text)
    return round(0.35 + base * 0.55, 4)  # 0.35–0.9 range

def estimate_intensity(text: str) -> float:
    """Intensity — emotional / assertion power signal."""
    base = _scalar(text[::-1])
    return round(0.25 + base * 0.65, 4)  # 0.25–0.9

def compute_SQI(rho: float, I: float) -> float:
    """Symbolic Quality Index — harmonic product"""
    return round(math.sqrt(rho * I), 4)