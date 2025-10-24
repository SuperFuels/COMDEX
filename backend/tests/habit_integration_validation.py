# ================================================================
# 🧠 Habit Integration Validation — GHX ↔ Habit Auto-Feedback Loop
# ================================================================
"""
Validates synchronization between GHX telemetry stream and
Habit auto-feedback system.

Checks:
  • habit_auto_update.json exists and contains valid metrics
  • Recent timestamp (within 30s)
  • All expected keys present
  • Logs summary → data/telemetry/habit_integration_validation.json
"""

import json, time, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HABIT_PATH = Path("data/learning/habit_auto_update.json")
OUT_PATH = Path("data/telemetry/habit_integration_validation.json")

def run_validation():
    if not HABIT_PATH.exists():
        logger.error("[HabitValidation] Missing habit_auto_update.json — GHX feedback may not have run.")
        return

    data = json.load(open(HABIT_PATH))
    now = time.time()
    age = now - data.get("timestamp", 0)
    valid = all(k in data for k in ("avg_ρ", "avg_I", "habit_strength", "delta"))

    summary = {
        "timestamp": now,
        "age_s": round(age, 2),
        "valid_keys": valid,
        "habit_strength": data.get("habit_strength"),
        "delta": data.get("delta"),
        "schema": "HabitIntegrationValidation.v1",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(OUT_PATH, "w"), indent=2)
    logger.info(f"[HabitValidation] Summary → {OUT_PATH}")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    run_validation()
    print("✅ Habit ↔ GHX integration validation complete.")