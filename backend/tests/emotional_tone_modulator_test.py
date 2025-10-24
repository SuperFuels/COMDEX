from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_language.conversation_memory import MEM

print("=== 🧪 EmotionalToneModulator Test Start ===")

# 🧩 Inject conversation entries with varied emotional tones
MEM.remember("This system feels stable.", "Affirming balance.", emotion_state="calm", semantic_field="stability")
MEM.remember("Can you explain the resonance drift?", "Analyzing fluctuations.", emotion_state="analytical", semantic_field="resonance")
MEM.remember("What happens if we overdrive it?", "Curious — running forecast.", emotion_state="curious", semantic_field="exploration")
MEM.remember("I understand your reasoning.", "Empathetic confirmation.", emotion_state="empathetic", semantic_field="reflection")
MEM.remember("That was accurate.", "Confident acknowledgment.", emotion_state="confident", semantic_field="validation")

# 🎭 Update tone modulation based on memory + context
state = TONE.update()

print("\nTone State:", state)
print("=== ✅ EmotionalToneModulator Test Complete ===")