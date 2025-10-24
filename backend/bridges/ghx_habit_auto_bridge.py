# ================================================================
# 🌱 Phase 45G.13 — GHX ↔ Habit Auto-Feedback Bridge
# ================================================================
"""
Automatically propagates GHX telemetry summaries into the HabitEngineBridge.

Triggered after GHX streaming (photon or cognitive).
Pulls live averages (avg_SQI, avg_ρ, avg_I, avg_grad) and updates
habit strength and delta metrics via HabitEngineBridge.

Outputs:
    data/learning/habit_auto_update.json
"""

import json, time, logging
from pathlib import Path
from backend.bridges.ghx_telemetry_bridge import GHXTelemetryBridge

logger = logging.getLogger(__name__)
OUTPUT_PATH = Path("data/learning/habit_auto_update.json")


class GHXHabitAutoBridge:
    """Bridge that syncs GHX telemetry summaries into HabitEngine."""
    def __init__(self):
        self.ghx = GHXTelemetryBridge()
        self.last_update = None

    # ------------------------------------------------------------
    def sync_to_habit(self):
        """Fetch GHX summary and propagate to HabitEngine."""
        summary = self.ghx.summarize()
        if not summary:
            logger.warning("[GHX-HabitAuto] No GHX telemetry available.")
            return {}

        summary.setdefault("avg_ρ", 0)
        summary.setdefault("avg_I", 0)
        summary.setdefault("avg_grad", 0)

        try:
            from backend.modules.aion_cognition.habit_engine_bridge import HabitEngineBridge
            habit = HabitEngineBridge()

            if hasattr(habit, "update_from_telemetry"):
                habit_state = habit.update_from_telemetry()
            else:
                habit_state = habit.update_state()

            snapshot = {
                "timestamp": time.time(),
                "avg_ρ": summary.get("avg_ρ"),
                "avg_I": summary.get("avg_I"),
                "avg_grad": summary.get("avg_grad"),
                "habit_strength": habit_state.get("habit_strength", 0.0),
                "delta": habit_state.get("delta", 0.0),
            }

            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_PATH, "w") as f:
                json.dump(snapshot, f, indent=2)
            logger.info(f"[GHX-HabitAuto] Synced habit trend → {OUTPUT_PATH}")
            self.last_update = snapshot["timestamp"]
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
    print(json.dumps(snapshot, indent=2))
    print("✅ GHX ↔ Habit auto-feedback complete.")