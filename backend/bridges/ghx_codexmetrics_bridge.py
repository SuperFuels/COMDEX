# ================================================================
# 🌐 Phase 45G.14 - CodexMetrics Telemetry Overlay Bridge (lazy + deterministic-safe)
# ================================================================
"""
Streams GHX↔Habit feedback metrics into CodexMetrics overlay.

Inputs:
    data/learning/habit_auto_update.json
Outputs:
    data/telemetry/codexmetrics_overlay.json
    (optionally -> GHX UI WebSocket endpoint)
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

HABIT_FEEDBACK_PATH = Path("data/learning/habit_auto_update.json")
OUTPUT_PATH = Path("data/telemetry/codexmetrics_overlay.json")


# ─────────────────────────────────────────────
# Determinism / quiet gates
# ─────────────────────────────────────────────
def _deterministic_time_enabled() -> bool:
    return os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"


def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1"


def _now_unix() -> float:
    return 0.0 if _deterministic_time_enabled() else time.time()


class GHXCodexMetricsBridge:
    def __init__(
        self,
        habit_path: Path = HABIT_FEEDBACK_PATH,
        output_path: Path = OUTPUT_PATH,
    ):
        self.habit_path = Path(habit_path)
        self.output_path = Path(output_path)
        self.last_update: Optional[float] = None

    # ------------------------------------------------------------
    def load_habit_feedback(self) -> Optional[Dict[str, Any]]:
        """Load latest habit auto-feedback JSON."""
        if not self.habit_path.exists():
            logger.warning("[CodexMetrics] No habit feedback found.")
            return None
        try:
            with self.habit_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("[CodexMetrics] Loaded habit feedback metrics.")
            return data
        except Exception as e:
            logger.error(f"[CodexMetrics] Failed to read habit feedback: {e}")
            return None

    # ------------------------------------------------------------
    def generate_overlay(self, habit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compose overlay telemetry payload for CodexMetrics."""
        ghx = habit_data.get("ghx_summary", habit_data) if isinstance(habit_data, dict) else {}
        overlay = {
            "timestamp": _now_unix(),
            "habit_strength": habit_data.get("habit_strength", ghx.get("habit_strength", 0)) if isinstance(habit_data, dict) else 0,
            "delta": habit_data.get("delta", ghx.get("delta", 0)) if isinstance(habit_data, dict) else 0,
            "avg_ρ": ghx.get("avg_ρ", 0),
            "avg_I": ghx.get("avg_I", 0),
            "avg_grad": ghx.get("avg_grad", 0),
            "source": "GHX↔Habit",
            "schema": "CodexMetricsOverlay.v1",
        }
        return overlay

    # ------------------------------------------------------------
    def export_overlay(self, overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Persist overlay data for GHX/Codex dashboard."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.output_path.open("w", encoding="utf-8") as f:
                json.dump(overlay, f, indent=2, ensure_ascii=False)
            self.last_update = float(overlay.get("timestamp", 0.0) or 0.0)
            logger.info(f"[CodexMetrics] Overlay updated -> {self.output_path}")
        except Exception as e:
            logger.error(f"[CodexMetrics] export_overlay failed: {e}")
            return {}
        return overlay

    # ------------------------------------------------------------
    def sync(self) -> Dict[str, Any]:
        """Perform full GHX->Habit->Codex sync pipeline."""
        habit_data = self.load_habit_feedback()
        if not habit_data:
            logger.warning("[CodexMetrics] Skipped - no habit data.")
            return {}
        overlay = self.generate_overlay(habit_data)
        return self.export_overlay(overlay)


# ─────────────────────────────────────────────
# Lazy singleton (NO import-time runtime bring-up)
# ─────────────────────────────────────────────
_BRIDGE: Optional[GHXCodexMetricsBridge] = None


def get_bridge() -> GHXCodexMetricsBridge:
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = GHXCodexMetricsBridge()
        if not _quiet_enabled():
            logger.info("[CodexMetrics] GHXCodexMetricsBridge initialized (lazy)")
    return _BRIDGE


class _BridgeProxy:
    def __getattr__(self, name: str):
        return getattr(get_bridge(), name)


# Back-compat: allow imports without eager init.
BRIDGE = _BridgeProxy()


# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bridge = get_bridge()
    overlay = bridge.sync()
    print(json.dumps(overlay, indent=2, ensure_ascii=False))
    print("✅ GHX↔Habit->CodexMetrics telemetry overlay complete.")