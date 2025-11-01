# backend/bridges/introspective_goal_bridge.py
# ============================================================
# Phase 36 - Introspective -> Goal Bridge
# Tessaris / Aion Research Division
# ============================================================

from __future__ import annotations
from pathlib import Path
import json
from typing import Optional, Dict, Any

# Import AKG + Goal Engine (Photon variant)
from backend.modules.aion_knowledge import knowledge_graph_core as akg
from backend.modules.aion_photon.goal_engine import GOALS

RSI_DRIFT_JSON = Path("data/analysis/rsi_drift_snapshot.json")

class IntrospectiveGoalBridge:
    """
    Phase 36: Monitors introspective metrics (self-accuracy, RSI drift)
    and spawns intrinsic goals when cognitive imbalance is detected.
    """

    def __init__(self, acc_threshold: float = 0.25, drift_threshold: float = 0.15):
        self.acc_threshold = acc_threshold
        self.drift_threshold = drift_threshold

    # ─────────────────────────────────────────────
    # Data readers
    # ─────────────────────────────────────────────
    def _read_self_accuracy(self) -> Optional[float]:
        recs = akg.search(subject="concept:global_meta", predicate="self_accuracy")
        if not recs:
            return None
        try:
            return float(recs[-1]["object"])
        except Exception:
            return None

    def _read_rsi_drift(self) -> Optional[float]:
        if not RSI_DRIFT_JSON.exists():
            return None
        try:
            data = json.loads(RSI_DRIFT_JSON.read_text())
            return float(data.get("rsi_drift", 0.0))
        except Exception:
            return None

    # ─────────────────────────────────────────────
    # Goal creation (adapted to your GoalEngine)
    # ─────────────────────────────────────────────
    def _spawn_goal(self, reason: str, details: Dict[str, Any]) -> Optional[dict]:
        name = f"auto_goal_{reason}"
        desc = f"Automatically spawned goal due to {reason}. Details: {details}"
        try:
            # Adapted for your GoalEngine interface
            if hasattr(GOALS, "create_goal"):
                g = GOALS.create_goal(name=name, description=desc, origin="IntrospectiveGoalBridge")
            else:
                # Fallback: manually append to active_goals if it's a list
                g = {"name": name, "description": desc, "origin": "IntrospectiveGoalBridge"}
                if hasattr(GOALS, "active_goals"):
                    GOALS.active_goals.append(g)
            return g
        except Exception as e:
            print(f"⚠️ Failed to create goal: {e}")
            return None
    # ─────────────────────────────────────────────
    # Core logic
    # ─────────────────────────────────────────────
    def run_once(self) -> Optional[dict]:
        """Perform one introspection cycle and possibly spawn a goal."""
        acc = self._read_self_accuracy()
        drift = self._read_rsi_drift()

        # Condition 1 - low self-accuracy
        if acc is not None and acc < self.acc_threshold:
            return self._spawn_goal(
                "low_self_accuracy",
                {"self_accuracy": acc, "threshold": self.acc_threshold},
            )

        # Condition 2 - excessive RSI drift
        if drift is not None and drift > self.drift_threshold:
            return self._spawn_goal(
                "high_rsi_drift",
                {"rsi_drift": drift, "threshold": self.drift_threshold},
            )

        return None

    # Alias for clarity in Aion introspection pipelines
    def scan_and_spawn_goals(self) -> Optional[dict]:
        return self.run_once()