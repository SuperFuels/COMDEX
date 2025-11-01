"""
Resonance Alignment Engine
────────────────────────────────────────────
Unifies and realigns SQI metrics (ρ, Ī) across Aion and Wiki Capsule layers.
Performs normalization and optionally triggers Aion resonance recalibration
when drift exceeds threshold.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

from backend.AION.resonance.resonance_engine import get_resonance, update_resonance


# ───────────────────────────────────────────────
# Dataclass Representation
# ───────────────────────────────────────────────
@dataclass
class ResonanceState:
    rho: float          # coherence coefficient (ρ)
    Ibar: float         # intelligence index (Ī)
    sqi_score: float    # combined SQI magnitude


# ───────────────────────────────────────────────
# Meta-Level Alignment
# ───────────────────────────────────────────────
def align_resonance(meta: Dict[str, Any]) -> ResonanceState:
    """
    Compute unified resonance metrics from capsule metadata.
    Args:
        meta: dict containing 'ρ', 'Ī', and 'sqi_score' fields.
    Returns:
        ResonanceState with normalized and coherence-adjusted values.
    """
    rho = float(meta.get("ρ", 0.0))
    Ibar = float(meta.get("Ī", 0.0))
    sqi = float(meta.get("sqi_score", 0.0))

    # Composite normalization (avoid division by zero)
    unified = (rho + Ibar + sqi) / 3.0 if (rho + Ibar + sqi) != 0 else 0.001
    rho_u = round(rho / unified, 4)
    Ibar_u = round(Ibar / unified, 4)
    sqi_u = round(sqi / unified, 4)

    return ResonanceState(rho=rho_u, Ibar=Ibar_u, sqi_score=sqi_u)


# ───────────────────────────────────────────────
# AION Realignment Bridge
# ───────────────────────────────────────────────
def resonance_realign(title: str, keywords: Optional[list] = None) -> Dict[str, Any]:
    """
    Force recalibration of a single capsule's resonance fields.
    This pulls the current Aion resonance state, recomputes drift,
    and triggers an update_resonance() if necessary.
    """
    current = get_resonance(title)
    if not current:
        print(f"[Realign] {title} not found - creating baseline.")
        return update_resonance(title, keywords)

    new_state = update_resonance(title, keywords or current.get("keywords", []))

    drift = new_state["SQI"] - current["SQI"]
    print(f"[Realign] {title}: ΔSQI={drift:+.3f} | ρ={new_state['ρ']:.3f} Ī={new_state['Ī']:.3f}")
    return new_state