from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_language.meta_dialogue_engine import META
from backend.modules.aion_language.conversation_memory import MEM

print("=== 🧪 Reflective Tone Coupling Test ===")

# 1. Simulate reflection outcomes
reflection_low = {"comment": "Resonance drift detected; coherence low.",
                  "metrics": {"tone": "neutral", "confidence": 0.3, "resonance": 0.2}}
reflection_conf = {"comment": "My confidence is limited while in analytical mode.",
                   "metrics": {"tone": "analytical", "confidence": 0.3, "resonance": 0.5}}
reflection_stable = {"comment": "Tone 'reflective' remains stable; coherence 0.65.",
                     "metrics": {"tone": "reflective", "confidence": 0.7, "resonance": 0.65}}

# 2. Run adjustments
TONE.adjust_from_reflection(reflection_low)
TONE.adjust_from_reflection(reflection_conf)
TONE.adjust_from_reflection(reflection_stable)

print("Final Tone State:", TONE.state)
print("=== ✅ Reflective Tone Coupling Test Complete ===")