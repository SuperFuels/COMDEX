"""
resonance_alignment.py
──────────────────────────────────────────────
Unifies SQI metrics (ρ, Ī) across Photon, Aion, and Wiki Capsule layers.
Each capsule’s meta block is normalized and merged into the
system-wide resonance state for coherence tracking.
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ResonanceState:
    rho: float          # coherence coefficient
    Ibar: float         # intelligence index
    sqi_score: float    # combined SQI magnitude

def align_resonance(meta: Dict[str, Any]) -> ResonanceState:
    """
    Compute unified resonance metrics from capsule metadata.
    Args:
        meta: dict containing 'ρ', 'Ī', and 'sqi_score' fields.
    Returns:
        ResonanceState with normalized values.
    """
    rho = float(meta.get("ρ", 0.0))
    Ibar = float(meta.get("Ī", 0.0))
    sqi = float(meta.get("sqi_score", 0.0))

    # Simple normalization: average + weighted adjustment
    unified = (rho + Ibar + sqi) / 3.0
    rho_u = round(rho / max(unified, 1e-9), 4)
    Ibar_u = round(Ibar / max(unified, 1e-9), 4)
    sqi_u = round(sqi / max(unified, 1e-9), 4)

    return ResonanceState(rho=rho_u, Ibar=Ibar_u, sqi_score=unified)