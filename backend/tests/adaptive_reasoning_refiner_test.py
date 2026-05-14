from backend.modules.aion_language.adaptive_reasoning_refiner import REASON
from backend.modules.aion_language.emotional_tone_modulator import TONE

print("=== 🧪 Adaptive Reasoning Refiner Test ===")
for tone in ["calm", "analytical", "reflective", "curious", "confident"]:
    TONE.state.update({"tone": tone, "confidence": 0.6, "energy": 0.5})
    print(f"\n--- Tone: {tone} ---")
    result = REASON.compute_bias()
    print(result)
print("=== ✅ Test Complete ===")