from backend.modules.aion_language.habit_encoding_engine import HABIT
from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_language.adaptive_reasoning_refiner import REASON
from backend.modules.aion_language.temporal_motivation_persistence import MOTIVE
from backend.modules.aion_language.goal_motivation_calibrator import CAL

print("=== 🧪 Habit Encoding Engine Test Start ===")

# Simulate stable states
TONE.state.update({"tone": "reflective", "confidence": 0.8, "energy": 0.5})
REASON.bias_state = {"depth": 1.1, "exploration": 0.9, "verbosity": 1.0}
MOTIVE.persistence_index = 0.85
MOTIVE.current_lr = 0.12
CAL.last_focus = 0.78

# Encode a few cycles
for _ in range(3):
    HABIT.encode()

summary = HABIT.summarize()
print("--- Habit Summary ---")
print(summary)

print("=== ✅ Habit Encoding Engine Test Complete ===")