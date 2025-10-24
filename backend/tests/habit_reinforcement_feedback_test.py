"""
Test — Phase 45E: Habit Reinforcement Feedback
"""

from backend.modules.aion_language.habit_reinforcement_feedback import FEED
from backend.modules.aion_language.habit_encoding_engine import HABIT
from backend.modules.aion_language.temporal_motivation_persistence import MOTIVE

print("=== 🧪 Habit Reinforcement Feedback Test Start ===")

# ✅ Initialize baseline habit and motivational state
# Run the engine’s internal encoding method (auto-tone)
if hasattr(HABIT, "encode"):
    HABIT.encode()
elif hasattr(HABIT, "encode_habit"):
    HABIT.encode_habit()
elif hasattr(HABIT, "store_habit"):
    HABIT.store_habit()
else:
    print("[TEST] ⚠️ No known encode/store habit method — skipping manual init.")

# Set motivational baseline
MOTIVE.last_persistence = 0.9
MOTIVE.avg_stability = 0.95
MOTIVE.avg_drift = 0.1

# Run several feedback cycles to test reinforcement behavior
for i in range(3):
    result = FEED.run_feedback_cycle()

print("\n--- Feedback Summary ---")
print(result)
print("=== ✅ Habit Reinforcement Feedback Test Complete ===")