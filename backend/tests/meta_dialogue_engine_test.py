from backend.modules.aion_language.meta_dialogue_engine import META
from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_language.conversation_memory import MEM

print("=== 🧪 Meta-Dialogue Engine Test Start ===")
# Stimulate tone & memory inputs
MEM.remember("The system feels steady.", "Affirming equilibrium.", emotion_state="calm")
MEM.remember("Resonance field is varying.", "Analytical monitoring.", emotion_state="analytical")
TONE.update()

# Generate reflection
reflection = META.reflect()
print("Reflection:", reflection)
print("=== ✅ Meta-Dialogue Engine Test Complete ===")