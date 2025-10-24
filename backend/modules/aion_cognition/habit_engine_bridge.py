# ================================================================
# 🧭 Phase 45G.8+ — Unified HabitEngine Telemetry Interface
# ================================================================
import json, time, logging
from pathlib import Path

logger = logging.getLogger(__name__)
HABIT_PATH = Path("data/learning/habit_state.json")
GHX_METRICS_PATH = Path("data/learning/cee_dual_metrics.json")  # fallback


class HabitEngineBridge:
    def __init__(self):
        self.habit_state = self._load_state()

    def _load_state(self):
        if HABIT_PATH.exists():
            with open(HABIT_PATH, "r") as f:
                return json.load(f)
        return {
            "timestamp": time.time(),
            "avg_SQI": 0.0,
            "avg_tone": 0.0,
            "avg_difficulty": 1.0,
            "habit_strength": 0.5,
        }

    def _save_state(self):
        HABIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HABIT_PATH, "w") as f:
            json.dump(self.habit_state, f, indent=2)

    # ------------------------------------------------------------
    # 🔁 Existing direct update (manual trigger)
    # ------------------------------------------------------------
    def update_state(self):
        logger.info("[Habit] Manual state update called.")
        return self.habit_state

    # ------------------------------------------------------------
    # 🌀 New unified telemetry-based update for auto-feedback
    # ------------------------------------------------------------
    # ------------------------------------------------------------
    # 🌀 Phase 45G.10 — GHX ↔ Habit Telemetry Bridge Integration
    # ------------------------------------------------------------
    def update_from_telemetry(self):
        """
        Integrate live GHX telemetry data to evolve habit strength and
        broadcast updates back into GHX telemetry feeds.

        This closes the feedback loop:
            CEE → GHX → HabitEngine → Trend → GHX (live sync)
        """
        metrics_path = Path("data/learning/cee_adaptive_metrics.json")
        if not metrics_path.exists() and GHX_METRICS_PATH.exists():
            metrics_path = GHX_METRICS_PATH

        if not metrics_path.exists():
            logger.warning("[Habit] No GHX telemetry found.")
            return None

        with open(metrics_path, "r") as f:
            telemetry = json.load(f)

        avg_sqi = telemetry.get("avg_SQI", 0.5)
        avg_tone = telemetry.get("avg_emotion", 0.5)
        avg_diff = telemetry.get("avg_difficulty", 1.0)

        # Weighted reinforcement curve
        habit_strength = self.habit_state.get("habit_strength", 0.5)
        delta = (avg_sqi * 0.4 + avg_tone * 0.3 - (avg_diff - 1.0) * 0.2)
        habit_strength = max(0.0, min(1.0, habit_strength * 0.9 + delta * 0.1))

        self.habit_state.update({
            "timestamp": time.time(),
            "avg_SQI": avg_sqi,
            "avg_tone": avg_tone,
            "avg_difficulty": avg_diff,
            "habit_strength": round(habit_strength, 3),
            "delta": round(delta, 3),
        })
        self._save_state()

        # 🔭 Push updated metrics to GHX dashboard
        from backend.bridges.ghx_habit_bridge import GHXHabitTelemetryBridge
        ghx_sync = GHXHabitTelemetryBridge()
        ghx_sync.sync_to_ghx()
        ghx_sync.broadcast()

        logger.info(f"[Habit] Updated habit state → {self.habit_state}")
        return self.habit_state

    # ================================================================
    # 📈 Phase 45G.9 — Habit Trend & Reinforcement Curves
    # ================================================================
    import matplotlib.pyplot as plt
    import pandas as pd

    HABIT_TREND_PATH = Path("data/learning/habit_trend.json")
    HABIT_TREND_IMG = Path("data/learning/habit_trend.png")

    def log_habit_trend(new_state: dict):
        """Append latest habit metrics to rolling trend log."""
        HABIT_TREND_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Load existing log
        trend = []
        if HABIT_TREND_PATH.exists():
            try:
                with open(HABIT_TREND_PATH, "r") as f:
                    trend = json.load(f)
            except Exception:
                trend = []

        # Compute delta
        prev_strength = trend[-1]["habit_strength"] if trend else 0.5
        delta = round(new_state["habit_strength"] - prev_strength, 4)

        entry = {
            "timestamp": new_state.get("timestamp", time.time()),
            "avg_SQI": new_state.get("avg_SQI", 0),
            "avg_tone": new_state.get("avg_tone", 0),
            "avg_difficulty": new_state.get("avg_difficulty", 1.0),
            "habit_strength": new_state.get("habit_strength", 0.5),
            "delta": delta,
        }
        trend.append(entry)

        # Keep recent 100 sessions max
        trend = trend[-100:]

        with open(HABIT_TREND_PATH, "w") as f:
            json.dump(trend, f, indent=2)

        logger.info(f"[HabitTrend] Logged habit evolution Δ={delta:+.4f}")
        plot_habit_trend(trend)
        return trend


    def plot_habit_trend(trend: list):
        """Render visual trend chart."""
        if not trend:
            return
        try:
            df = pd.DataFrame(trend)
            plt.figure(figsize=(8, 4))
            plt.plot(df["timestamp"], df["habit_strength"], marker="o", label="Habit Strength")
            plt.plot(df["timestamp"], df["avg_SQI"], linestyle="--", label="Avg SQI", alpha=0.7)
            plt.xlabel("Time")
            plt.ylabel("Value")
            plt.title("AION Habit Reinforcement Trend")
            plt.legend()
            plt.tight_layout()
            HABIT_TREND_IMG.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(HABIT_TREND_IMG)
            plt.close()
            logger.info(f"[HabitTrend] Chart saved → {HABIT_TREND_IMG}")
        except Exception as e:
            logger.warning(f"[HabitTrend] Plotting failed: {e}")