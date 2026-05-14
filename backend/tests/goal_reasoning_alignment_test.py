from backend.modules.aion_photon.goal_reasoning_alignment import ALIGN
from backend.modules.aion_language.adaptive_reasoning_refiner import REASON

print("=== 🧪 Goal Reasoning Alignment Test Start ===")

# Simulate reasoning bias propagation
REASON.reasoning_bias = {"depth": 1.22, "exploration": 1.12, "verbosity": 1.02}
entry = ALIGN.propagate_bias()

print("\n--- Alignment Result ---")
print(entry)
print("=== ✅ Goal Reasoning Alignment Test Complete ===")