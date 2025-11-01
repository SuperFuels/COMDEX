# ================================================================
# 🌐 Phase 45G.14 - CodexMetrics Telemetry Overlay Bridge
# ================================================================
"""
Streams GHX↔Habit feedback metrics into CodexMetrics overlay.

Inputs:
    data/learning/habit_auto_update.json
Outputs:
    data/telemetry/codexmetrics_overlay.json
    (optionally -> GHX UI WebSocket endpoint)
"""

import json, time, logging
from pathlib import Path

logger = logging.getLogger(__name__)

HABIT_FEEDBACK_PATH = Path("data/learning/habit_auto_update.json")
OUTPUT_PATH = Path("data/telemetry/codexmetrics_overlay.json")


class GHXCodexMetricsBridge:
    def __init__(self):
        self.last_update = None
        self.HABIT_PATH = Path("data/learning/habit_auto_update.json")
        self.OUTPUT_PATH = Path("data/telemetry/codexmetrics_overlay.json")

    # ------------------------------------------------------------
    def load_habit_feedback(self):
        """Load latest habit auto-feedback JSON."""
        if not HABIT_FEEDBACK_PATH.exists():
            logger.warning("[CodexMetrics] No habit feedback found.")
            return None
        try:
            data = json.load(open(HABIT_FEEDBACK_PATH))
            logger.info("[CodexMetrics] Loaded habit feedback metrics.")
            return data
        except Exception as e:
            logger.error(f"[CodexMetrics] Failed to read habit feedback: {e}")
            return None

    # ------------------------------------------------------------
    def generate_overlay(self, habit_data):
        """Compose overlay telemetry payload for CodexMetrics."""
        ghx = habit_data.get("ghx_summary", habit_data)
        overlay = {
            "timestamp": time.time(),
            "habit_strength": habit_data.get("habit_strength", ghx.get("habit_strength", 0)),
            "delta": habit_data.get("delta", ghx.get("delta", 0)),
            "avg_ρ": ghx.get("avg_ρ", 0),
            "avg_I": ghx.get("avg_I", 0),
            "avg_grad": ghx.get("avg_grad", 0),
            "source": "GHX↔Habit",
            "schema": "CodexMetricsOverlay.v1"
        }
        return overlay

    # ------------------------------------------------------------
    def sync_overlay(self):
        """Load latest habit feedback and propagate to CodexMetrics overlay."""
        try:
            if not self.HABIT_PATH.exists():
                logger.warning("[CodexMetrics] No habit feedback metrics found.")
                return {}

            with open(self.HABIT_PATH) as f:
                habit_data = json.load(f)

            overlay = {
                "timestamp": time.time(),
                "habit_strength": habit_data.get("habit_strength", 0),
                "delta": habit_data.get("delta", 0),
                "avg_ρ": habit_data.get("avg_ρ", 0),
                "avg_I": habit_data.get("avg_I", 0),
                "avg_grad": habit_data.get("avg_grad", 0),
                "source": "GHX↔Habit",
                "schema": "CodexMetricsOverlay.v1",
            }

            self.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.OUTPUT_PATH, "w") as f:
                json.dump(overlay, f, indent=2)
            logger.info(f"[CodexMetrics] Overlay updated -> {self.OUTPUT_PATH}")
            return overlay

        except Exception as e:
            logger.error(f"[CodexMetrics] sync_overlay failed: {e}")
            return {}

    # ------------------------------------------------------------
    def export_overlay(self, overlay):
        """Persist overlay data for GHX/Codex dashboard."""
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        json.dump(overlay, open(OUTPUT_PATH, "w"), indent=2)
        self.last_update = overlay["timestamp"]
        logger.info(f"[CodexMetrics] Overlay updated -> {OUTPUT_PATH}")
        return overlay

    # ------------------------------------------------------------
    def sync(self):
        """Perform full GHX->Habit->Codex sync pipeline."""
        habit_data = self.load_habit_feedback()
        if not habit_data:
            logger.warning("[CodexMetrics] Skipped - no habit data.")
            return {}
        overlay = self.generate_overlay(habit_data)
        return self.export_overlay(overlay)


# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    bridge = GHXCodexMetricsBridge()
    overlay = bridge.sync()
    print(json.dumps(overlay, indent=2))
    print("✅ GHX↔Habit->CodexMetrics telemetry overlay complete.")