# ================================================================
# 🌱 Phase 45G.13 - GHX ↔ Habit Auto-Feedback Bridge (deterministic/quiet aware)
# ================================================================
"""
Automatically propagates GHX telemetry summaries into the HabitEngineBridge.

Triggered after GHX streaming (photon or cognitive).
Pulls live averages (avg_SQI, avg_ρ, avg_I, avg_grad) and updates
habit strength and delta metrics via HabitEngineBridge.

Outputs:
    data/learning/habit_auto_update.json

Notes:
- No import-time bring-up of GHXTelemetryBridge (lazy).
- Deterministic timestamp when TESSARIS_DETERMINISTIC_TIME=1.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
OUTPUT_PATH = Path("data/learning/habit_auto_update.json")


# ─────────────────────────────────────────────
# Determinism / quiet gates
# ─────────────────────────────────────────────
def _deterministic_time_enabled() -> bool:
    return os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"


def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1"


def _now() -> float:
    return 0.0 if _deterministic_time_enabled() else time.time()


# Lazy import helper (avoid eager runtime bring-up)
def _get_ghx() -> Any:
    from backend.bridges.ghx_telemetry_bridge import GHXTelemetryBridge
    return GHXTelemetryBridge()


class GHXHabitAutoBridge:
    """Bridge that syncs GHX telemetry summaries into HabitEngine."""
    def __init__(self):
        self._ghx: Optional[Any] = None
        self.last_update: Optional[float] = None

    def _ghx_bridge(self) -> Any:
        if self._ghx is None:
            self._ghx = _get_ghx()
        return self._ghx

    # ------------------------------------------------------------
    def sync_to_habit(self) -> Dict[str, Any]:
        """Fetch GHX summary and propagate to HabitEngine."""
        try:
            summary = self._ghx_bridge().summarize()
        except Exception as e:
            logger.error(f"[GHX-HabitAuto] GHX summarize failed: {e}")
            return {}

        if not summary:
            logger.warning("[GHX-HabitAuto] No GHX telemetry available.")
            return {}

        # Defaults
        summary = dict(summary)
        summary.setdefault("avg_ρ", 0.0)
        summary.setdefault("avg_I", 0.0)
        summary.setdefault("avg_grad", 0.0)

        try:
            from backend.modules.aion_cognition.habit_engine_bridge import HabitEngineBridge
            habit = HabitEngineBridge()

            if hasattr(habit, "update_from_telemetry"):
                habit_state = habit.update_from_telemetry()
            else:
                habit_state = habit.update_state()

            habit_state = dict(habit_state) if isinstance(habit_state, dict) else {}

            snapshot: Dict[str, Any] = {
                "timestamp": _now(),
                "avg_ρ": summary.get("avg_ρ"),
                "avg_I": summary.get("avg_I"),
                "avg_grad": summary.get("avg_grad"),
                "habit_strength": habit_state.get("habit_strength", 0.0),
                "delta": habit_state.get("delta", 0.0),
                "schema": "GHXHabitAutoUpdate.v1",
                "source": "GHX↔HabitAuto",
            }

            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with OUTPUT_PATH.open("w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)

            logger.info(f"[GHX-HabitAuto] Synced habit trend -> {OUTPUT_PATH}")
            self.last_update = float(snapshot["timestamp"]) if isinstance(snapshot.get("timestamp"), (int, float)) else None
            return snapshot

        except Exception as e:
            logger.error(f"[GHX-HabitAuto] HabitEngine sync failed: {e}")
            return {}


# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bridge = GHXHabitAutoBridge()
    snapshot = bridge.sync_to_habit()
    if not _quiet_enabled():
        print(json.dumps(snapshot, indent=2))
        print("✅ GHX ↔ Habit auto-feedback complete.")
