# ================================================================
# 🌐 Phase 45G.10 - GHX ↔ Habit Telemetry Bridge (deterministic/quiet aware)
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

Notes:
- No import-time runtime bring-up.
- Deterministic timestamp when TESSARIS_DETERMINISTIC_TIME=1.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

HABIT_TREND_PATH = Path("data/learning/habit_trend.json")
CEE_METRICS_PATH = Path("data/learning/cee_dual_metrics.json")
GHX_HABIT_FEED_PATH = Path("data/telemetry/ghx_habit_feed.json")


# ─────────────────────────────────────────────
# Determinism / quiet gates
# ─────────────────────────────────────────────
def _deterministic_time_enabled() -> bool:
    return os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"


def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1"


def _now() -> float:
    return 0.0 if _deterministic_time_enabled() else time.time()


JSONLike = Union[Dict[str, Any], List[Any]]


class GHXHabitTelemetryBridge:
    def __init__(
        self,
        *,
        trend_path: Path = HABIT_TREND_PATH,
        metrics_path: Path = CEE_METRICS_PATH,
        out_path: Path = GHX_HABIT_FEED_PATH,
    ):
        self.trend_path = trend_path
        self.metrics_path = metrics_path
        self.out_path = out_path

        self.trend: List[Dict[str, Any]] = self._load_list(self.trend_path)
        self.metrics: Dict[str, Any] = self._load_dict(self.metrics_path)
        self.output: Dict[str, Any] = {}

    # ------------------------------------------------------------
    @staticmethod
    def _load_json(path: Path) -> JSONLike:
        if not path.exists():
            logger.warning(f"[GHX-Habit] Missing data source: {path}")
            return []
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[GHX-Habit] Failed to parse {path}: {e}")
            return []

    def _load_list(self, path: Path) -> List[Dict[str, Any]]:
        v = self._load_json(path)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
        return []

    def _load_dict(self, path: Path) -> Dict[str, Any]:
        v = self._load_json(path)
        if isinstance(v, dict):
            return dict(v)
        return {}

    # ------------------------------------------------------------
    def compute_slope(self) -> float:
        """Compute habit slope (reinforcement trajectory)."""
        if len(self.trend) < 2:
            return 0.0

        vals: List[float] = []
        for row in self.trend:
            try:
                vals.append(float(row.get("habit_strength")))
            except Exception:
                continue

        if len(vals) < 2:
            return 0.0

        diffs = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
        if not diffs:
            return 0.0

        try:
            return round(float(mean(diffs)), 5)
        except Exception:
            return 0.0

    # ------------------------------------------------------------
    def sync_to_ghx(self) -> Dict[str, Any] | None:
        """Aggregate habit trend + cognitive metrics into GHX feed."""
        if not self.trend:
            logger.warning("[GHX-Habit] No habit trend data to sync.")
            return None

        latest = self.trend[-1] if isinstance(self.trend[-1], dict) else {}
        slope = self.compute_slope()
        cee_avg = 0.0
        try:
            cee_avg = float(self.metrics.get("avg_SQI", 0.0))
        except Exception:
            cee_avg = 0.0

        payload: Dict[str, Any] = {
            "timestamp": _now(),
            "habit_strength": float(latest.get("habit_strength", 0.5) or 0.5),
            "delta": float(latest.get("delta", 0.0) or 0.0),
            "trend_slope": float(slope),
            "avg_SQI": float(cee_avg),
            "avg_tone": float(latest.get("avg_tone", 0.0) or 0.0),
            "avg_difficulty": float(latest.get("avg_difficulty", 1.0) or 1.0),
            "schema": "GHXHabitFeed.v1",
            "source": "GHX↔Habit",
        }

        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        with self.out_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        self.output = payload
        logger.info(f"[GHX-Habit] Feed exported -> {self.out_path}")
        return payload

    # ------------------------------------------------------------
    def broadcast(self) -> bool:
        """(Optional) Simulated REST/WS broadcast to GHX UI."""
        logger.info(f"[GHX-Habit] Broadcasting live feed: {self.output}")
        return True


# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ghx_habit = GHXHabitTelemetryBridge()
    feed = ghx_habit.sync_to_ghx()
    if feed:
        ghx_habit.broadcast()
        if not _quiet_enabled():
            print(json.dumps(feed, indent=2))
            print("✅ GHX ↔ Habit Telemetry Bridge synchronization complete.")
