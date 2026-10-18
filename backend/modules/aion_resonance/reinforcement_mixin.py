# backend/modules/aion_resonance/reinforcement_mixin.py
# ───────────────────────────────────────────────
# ResonantReinforcementMixin
# Shared reinforcement + heartbeat manager + optimizer hooks
# ───────────────────────────────────────────────

import json
import time
from pathlib import Path

from backend.modules.aion_learning.vault_store import AionLearningVaultStore

# ✅ Correct import path (this file exists in your tree)
from backend.modules.aion_resonance.resonant_heartbeat_monitor import ResonanceHeartbeat


class ResonantReinforcementMixin:
    def __init__(
        self,
        name: str,
        learning_rate: float = 0.05,
        *,
        vault_store: AionLearningVaultStore | None = None,
        history_path: str | Path | None = None,
    ):
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
        self.history_file = Path(
            history_path or f"data/telemetry/{name}_resonance_history.json"
        )
        self.reinforcement_vault = vault_store or AionLearningVaultStore(
            auto_configure=history_path is None
        )

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
            if self.reinforcement_vault.enabled:
                event_id = f"resonance-reinforcement-{self.name}-{time.time_ns()}"
                self.reinforcement_vault.append_event(event_id, {
                    **record,
                    "event_id": event_id,
                    "event_type": "resonance_reinforcement_snapshot",
                    "engine_name": self.name,
                    "ts_utc": record["timestamp"],
                })
                return
            data = []
            if self.history_file.is_file():
                data = json.loads(self.history_file.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    data = []
            data.append(record)
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text(
                json.dumps(data[-500:], indent=2), encoding="utf-8"
            )
        except Exception as e:
            print(f"[{self.name}] ⚠ Failed to record resonance: {e}")

    def get_reinforcement_history(self, limit: int = 500) -> list[dict]:
        if self.reinforcement_vault.enabled:
            rows = self.reinforcement_vault.list_events(
                kind="resonance_reinforcement_snapshot"
            )
            rows = [row for row in rows if row.get("engine_name") == self.name]
            return rows[-max(0, int(limit)):]
        if not self.history_file.is_file():
            return []
        try:
            value = json.loads(self.history_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        rows = [dict(row) for row in value if isinstance(row, dict)] if isinstance(value, list) else []
        return rows[-max(0, int(limit)):]
