from backend.modules.aion_language.conversation_memory import MEM
from backend.modules.aion_language.semantic_context_manager import CTX
from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_language.context_akg_bridge import CTX_AKG

print("=== 🧪 Context↔AKG Bridge Test Start ===")

# Simulate recent conversation
MEM.remember("System feels balanced.", "Affirming equilibrium.", emotion_state="calm", semantic_field="stability")
MEM.remember("Analyze the resonance pattern.", "Computing harmonic spectrum.", emotion_state="analytical", semantic_field="resonance")
MEM.remember("Could it self-correct?", "Curious — evaluating self-regulation.", emotion_state="curious", semantic_field="adaptation")

# Update tone based on recent dialogue
TONE.update()

# Export current state to AKG
export = CTX_AKG.export_to_AKG()

print("\n--- Exported Context Node ---")
print(export)

# Summarize export history
print("\n--- Export History Summary ---")
print(CTX_AKG.summarize_history())

print("=== ✅ Context↔AKG Bridge Test Complete ===")