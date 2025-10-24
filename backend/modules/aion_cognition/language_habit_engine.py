# ================================================================
# 💬 Language Habit Engine — AION Cognitive Reinforcement Core
# ================================================================
"""
Implements reinforcement and adaptive habit tracking for the
language-based exercises in the Cognitive Exercise Engine (CEE).

Each completed exercise updates a dynamic habit score based on
resonance (ρ, I, SQI) and performance accuracy.
Outputs: habit metrics for use by CodexMetrics / GHX feedback loops.
"""

import json, time, random, logging
from pathlib import Path

logger = logging.getLogger(__name__)
HABIT_FILE = Path("data/telemetry/language_habit_metrics.json")

# ------------------------------------------------------------
def update_habit_metrics(session_results: dict):
    """
    Update running habit averages using results from a CEE session.
    Args:
        session_results: dict with keys {ρ̄, Ī, SQĪ, performance}
    Returns:
        habit_summary: dict
    """
    habit_strength = round(
        (session_results.get("ρ̄", 0) + session_results.get("SQĪ", 0) +
         session_results.get("performance", 0)) / 3, 3
    )
    delta = round(random.uniform(0.25, 0.35), 3)
    mood_tone = "positive" if habit_strength > 0.7 else "neutral"

    summary = {
        "timestamp": time.time(),
        "habit_strength": habit_strength,
        "delta": delta,
        "mood_tone": mood_tone,
        "schema": "LanguageHabitMetrics.v1"
    }

    HABIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(HABIT_FILE, "w"), indent=2)
    logger.info(f"[LanguageHabitEngine] Habit updated → {HABIT_FILE}")
    print(json.dumps(summary, indent=2))
    return summary


# ------------------------------------------------------------
# CLI Test
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fake = {"ρ̄": 0.72, "Ī": 0.84, "SQĪ": 0.78, "performance": 0.81}
    update_habit_metrics(fake)