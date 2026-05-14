from backend.modules.aion_language.goal_motivation_calibrator import CAL
from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_language.adaptive_reasoning_refiner import REASON

print("=== 🧪 Motivational Resonance Calibration Test Start ===")

# Simulate a reflective emotional state + reasoning bias
TONE.state.update({"tone": "reflective", "confidence": 0.85, "energy": 0.55})
REASON.reasoning_bias.update({"depth": 1.1, "exploration": 1.0, "verbosity": 1.1})

result = CAL.calibrate_motivation()

print("\n--- Calibration Result ---")
print(result)
print("=== ✅ Motivational Resonance Calibration Test Complete ===")