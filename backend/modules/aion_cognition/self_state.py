# backend/modules/aion_cognition/self_state.py
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.aion_cognition.cau_authority import get_authority_state
from backend.modules.aion_cognition.denial_explain import denial_explanation_line

# Hard limits (Phase 2)
_MAX_LEN = 140  # one-line, demo-friendly
_GOAL_DEFAULT = "maintain_coherence"


def _f_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _clip(s: str, max_len: int = _MAX_LEN) -> str:
    s = (s or "").replace("\n", " ").replace("\r", " ").strip()
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)].rstrip() + "…"


def self_state_summary(goal: str = _GOAL_DEFAULT, max_len: int = _MAX_LEN) -> str:
    """
    One-line, fact-only self status.
    No opinions. No anthropomorphism. CAU is the authority.

    Output is hard-capped to max_len and safe under missing/str/None metrics.
    """
    from backend.modules.aion_cognition.denial_explain import denial_explanation_line

    st: Dict[str, Any] = get_authority_state(goal=goal) or {}

    allow = bool(st.get("allow_learn", False))
    adr = bool(st.get("adr_active", False))
    cooldown = st.get("cooldown_s", 0) or 0
    deny_reason = st.get("deny_reason") or None

    S = _f_float(st.get("S"))
    H = _f_float(st.get("H"))
    Phi = _f_float(st.get("Phi"))

    # ADR dominates (still denial, but keep explicit ADR signal + include goal)
    if adr:
        base = f"deny_learn=1 adr_active=1 cooldown_s={int(cooldown)} goal={goal}"
        return _clip(base, max_len=max_len)

    # Denied: MUST be goal-tagged, single-line, no prose
    if not allow:
        line = denial_explanation_line(goal=goal, deny_reason=deny_reason)
        if cooldown:
            line = f"{line} cooldown_s={int(cooldown)}"
        return _clip(line, max_len=max_len)

    # Allowed: stable key/value tokens (keep your current style)
    parts = ["allow_learn=1"]
    if S is not None:
        parts.append(f"S={S:.2f}")
    if H is not None:
        parts.append(f"H≈{H:.2e}")
    if Phi is not None:
        parts.append(f"Φ={Phi:.3f}")
    parts.append(f"goal={goal}")

    return _clip("; ".join(parts), max_len=max_len)