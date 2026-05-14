# backend/modules/aion_resonance/reinforcement_mixin.py
# ───────────────────────────────────────────────
# ResonantReinforcementMixin
# Shared reinforcement + heartbeat manager + optimizer hooks
# ───────────────────────────────────────────────

import os
import json
import time

# ✅ Correct import path (this file exists in your tree)
from backend.modules.aion_resonance.resonant_heartbeat_monitor import ResonanceHeartbeat


class ResonantReinforcementMixin:
    def __init__(self, name: str, learning_rate: float = 0.05):
        self.name = name
        self.learning_rate = float(learning_rate)

        # Local heartbeat instance with live state
        self.heartbeat = ResonanceHeartbeat(namespace=name)

        # Initialize expected attrs so downstream code never breaks
        if not hasattr(self.heartbeat, "coherence"):
            self.heartbeat.coherence = 0.85
        if not hasattr(self.heartbeat, "entropy"):
            self.heartbeat.entropy = 0.15

        # Track latest SQI locally (and mirror on heartbeat for convenience)
        self.last_sqi = self._compute_sqi(self.heartbeat.coherence, self.heartbeat.entropy)
        setattr(self.heartbeat, "sqi", self.last_sqi)

        # Per-engine resonance history for dashboards
        self.history_file = f"data/telemetry/{name}_resonance_history.json"
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

        # Optional knobs that the optimizer might tune (existence-checked later)
        # Engines can define in their own __init__:
        #   self.exploration, self.risk_bias, self.branch_temp, self.search_temp
        self.optimizer_extras = {}

    # ───────────────────────────────────────────
    # Public reinforcement API
    # ───────────────────────────────────────────
    def update_resonance_feedback(self, outcome_score: float, reason: str = ""):
        """
        Adjust resonance metrics based on subsystem performance.
        outcome_score ∈ R (recommend 0..1) - positive improves coherence / reduces entropy.
        """
        try:
            outcome = float(outcome_score)
        except Exception:
            outcome = 0.0

        delta = outcome * float(self.learning_rate)

        # Update local heartbeat state (bounded)
        self.heartbeat.coherence = max(0.0, min(1.0, self.heartbeat.coherence + delta))
        self.heartbeat.entropy   = max(0.0, min(1.0, self.heartbeat.entropy   - delta * 0.8))

        # Update SQI (store both locally and on the heartbeat for convenience)
        self.last_sqi = self._compute_sqi(self.heartbeat.coherence, self.heartbeat.entropy)
        setattr(self.heartbeat, "sqi", self.last_sqi)

        # Emit a pulse so registered listeners can react
        # (ResonanceHeartbeat defines emit(delta: float))
        try:
            self.heartbeat.emit(delta)
        except Exception as e:
            print(f"[{self.name}] ⚠ heartbeat.emit failed: {e}")

        # Persist a snapshot for dashboards
        self._record_snapshot(outcome, reason or f"Outcome {outcome:.2f}")

    # ───────────────────────────────────────────
    # Optimizer hooks (safe defaults)
    # ───────────────────────────────────────────
    def get_resonance_snapshot(self) -> dict:
        """
        Engines may override; defaults use heartbeat + last_sqi + any optimizer_extras.
        """
        return {
            "coherence": float(getattr(self.heartbeat, "coherence", 0.5)),
            "entropy":   float(getattr(self.heartbeat, "entropy", 0.5)),
            "sqi":       float(getattr(self, "last_sqi", 0.6)),
            "extras":    dict(getattr(self, "optimizer_extras", {})),
        }

    def apply_optimizer_delta(self, deltas: dict):
        """
        Generic knobs - if the engine defines an attribute, nudge it a tiny amount.
        Safe, bounded, and observable (advisory-only mode).
        """
        def _n(name: str, default: float = 0.0):
            if name in deltas:
                try:
                    cur = float(getattr(self, name, default))
                except Exception:
                    cur = float(default)
                try:
                    delta = float(deltas[name])
                except Exception:
                    delta = 0.0
                setattr(self, name, cur + delta)

        # Common knobs the optimizer may touch (engines can choose which ones they expose)
        for knob in ("exploration", "risk_bias", "branch_temp", "search_temp", "learning_rate"):
            _n(knob)

        # Expose visible set for dashboards
        visible = {}
        for k in ("exploration", "risk_bias", "branch_temp", "search_temp", "learning_rate"):
            if hasattr(self, k):
                try:
                    visible[k] = float(getattr(self, k))
                except Exception:
                    pass
        self.optimizer_extras = {**getattr(self, "optimizer_extras", {}), **visible}

    # ───────────────────────────────────────────
    # Internals
    # ───────────────────────────────────────────
    def _compute_sqi(self, coherence: float, entropy: float) -> float:
        # Simple normalized score ∈ [0,1]
        return round((float(coherence) - float(entropy) + 1.0) / 2.0, 3)

    def _record_snapshot(self, outcome_score: float, note: str = ""):
        """Append timestamped resonance record for dashboard tracking."""
        record = {
            "timestamp": time.time(),
            "coherence": float(getattr(self.heartbeat, "coherence", 0.5)),
            "entropy":   float(getattr(self.heartbeat, "entropy", 0.5)),
            "sqi":       float(getattr(self, "last_sqi", 0.6)),
            "outcome":   float(outcome_score),
            "note":      note,
            "extras":    dict(getattr(self, "optimizer_extras", {})),
        }
        try:
            data = []
            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
            data.append(record)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data[-500:], f, indent=2)
        except Exception as e:
            print(f"[{self.name}] ⚠ Failed to record resonance: {e}")