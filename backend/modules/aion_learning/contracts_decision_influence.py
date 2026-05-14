from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


ALLOWED_TOP_LEVEL_KEYS = {
    "setup_confidence_weights",
    "pair_session_preferences",
    "stand_down_sensitivity",
    "llm_trust_weights",
    "event_caution_multipliers",
}

FORBIDDEN_KEYS_HINTS = {
    "max_risk_per_trade",
    "max_daily_risk",
    "max_weekly_risk",
    "position_sizing",
    "execution_authorization",
    "live_trading_enabled",
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


@dataclass
class DecisionInfluenceUpdate:
    """
    Governed writable influence update (Sprint 3).
    Safety: this contract explicitly excludes risk invariants and execution auth.
    """

    session_id: str
    turn_id: str
    source: str  # e.g. "learning_runtime", "llm_debrief", "cluster_review"
    reason: str
    updates: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "DecisionInfluenceUpdate":
        if not str(self.session_id).strip():
            raise ValueError("session_id is required")
        if not str(self.turn_id).strip():
            raise ValueError("turn_id is required")
        if not str(self.source).strip():
            raise ValueError("source is required")
        if not str(self.reason).strip():
            raise ValueError("reason is required")
        if not isinstance(self.updates, dict):
            raise ValueError("updates must be a dict")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")

        # Block obvious forbidden attempts anywhere at top level, and unknown sections.
        for k in self.updates.keys():
            if k in FORBIDDEN_KEYS_HINTS:
                raise ValueError(f"forbidden decision influence key: {k}")
            if k not in ALLOWED_TOP_LEVEL_KEYS:
                raise ValueError(f"unsupported decision influence section: {k}")

        self.confidence = _clamp(self.confidence, 0.0, 1.0)
        return self