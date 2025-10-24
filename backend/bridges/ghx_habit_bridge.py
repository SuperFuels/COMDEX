# ================================================================
# 🌐 Phase 45G.10 — GHX ↔ Habit Telemetry Bridge
# ================================================================
"""
Streams habit evolution metrics (habit_strength, Δhabit, trend slope)
into GHX telemetry for real-time visualization.

Inputs:
    data/learning/habit_trend.json
    data/learning/cee_dual_metrics.json
Outputs:
    data/telemetry/ghx_habit_feed.json
    Optional REST/WS broadcast (for GHX UI)
"""

import json, time, logging
from pathlib import Path
from statistics import mean

logger = logging.getLogger(__name__)

HABIT_TREND_PATH = Path("data/learning/habit_trend.json")
CEE_METRICS_PATH = Path("data/learning/cee_dual_metrics.json")
GHX_HABIT_FEED_PATH = Path("data/telemetry/ghx_habit_feed.json")


class GHXHabitTelemetryBridge:
    def __init__(self):
        self.trend = self._load(HABIT_TREND_PATH)
        self.metrics = self._load(CEE_METRICS_PATH)
        self.output = {}

    # ------------------------------------------------------------
    def _load(self, path: Path):
        if not path.exists():
            logger.warning(f"[GHX-Habit] Missing data source: {path}")
            return []
        with open(path, "r") as f:
            try:
                return json.load(f)
            except Exception as e:
                logger.warning(f"[GHX-Habit] Failed to parse {path}: {e}")
                return []

    # ------------------------------------------------------------
    def compute_slope(self):
        """Compute habit slope (reinforcement trajectory)."""
        if len(self.trend) < 2:
            return 0.0
        diffs = [t["habit_strength"] - self.trend[i - 1]["habit_strength"]
                 for i, t in enumerate(self.trend) if i > 0]
        return round(mean(diffs), 5)

    # ------------------------------------------------------------
    def sync_to_ghx(self):
        """Aggregate habit trend + cognitive metrics into GHX feed."""
        if not self.trend:
            logger.warning("[GHX-Habit] No habit trend data to sync.")
            return None

        latest = self.trend[-1]
        slope = self.compute_slope()
        cee_avg = self.metrics.get("avg_SQI", 0) if isinstance(self.metrics, dict) else 0

        payload = {
            "timestamp": time.time(),
            "habit_strength": latest.get("habit_strength", 0.5),
            "delta": latest.get("delta", 0.0),
            "trend_slope": slope,
            "avg_SQI": cee_avg,
            "avg_tone": latest.get("avg_tone", 0.0),
            "avg_difficulty": latest.get("avg_difficulty", 1.0),
        }

        GHX_HABIT_FEED_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(GHX_HABIT_FEED_PATH, "w") as f:
            json.dump(payload, f, indent=2)

        self.output = payload
        logger.info(f"[GHX-Habit] Feed exported → {GHX_HABIT_FEED_PATH}")
        return payload

    # ------------------------------------------------------------
    def broadcast(self):
        """(Optional) Simulated REST/WS broadcast to GHX UI."""
        # In production: use FastAPI WebSocket or REST push
        logger.info(f"[GHX-Habit] Broadcasting live feed: {self.output}")
        return True


# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ghx_habit = GHXHabitTelemetryBridge()
    feed = ghx_habit.sync_to_ghx()
    if feed:
        ghx_habit.broadcast()
        print(json.dumps(feed, indent=2))
        print("✅ GHX ↔ Habit Telemetry Bridge synchronization complete.")