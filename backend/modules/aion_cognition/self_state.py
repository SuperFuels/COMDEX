# backend/modules/aion_cognition/self_state.py

from __future__ import annotations

from typing import Any, Optional
from backend.modules.aion_cognition.cau_authority import get_authority_state


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def self_state_summary(goal: str = "maintain_coherence") -> str:
    """
    One-line, fact-only self status.
    No opinions. No anthropomorphism. CAU is the authority.
    """
    st = get_authority_state(goal=goal)

    allow = bool(st.get("allow_learn", False))
    adr = bool(st.get("adr_active", False))
    cooldown = int(st.get("cooldown_s", 0) or 0)
    deny = st.get("deny_reason") or None

    S = _to_float(st.get("S"))
    H = _to_float(st.get("H"))
    Phi = _to_float(st.get("Phi"))

    if adr:
        if cooldown:
            return f"Learning paused (ADR active); cooldown={cooldown}s; goal={goal}."
        return f"Learning paused (ADR active); goal={goal}."

    if not allow:
        reason = deny or "UNSPECIFIED"
        if cooldown:
            return f"Learning denied ({reason}); cooldown={cooldown}s; goal={goal}."
        return f"Learning denied ({reason}); goal={goal}."

    parts = ["Learning allowed"]
    if S is not None:
        parts.append(f"S={S:.2f}")
    if H is not None:
        parts.append(f"H≈{H:.2e}")
    if Phi is not None:
        parts.append(f"Φ={Phi:.3f}")
    return "; ".join(parts) + f"; goal={goal}."