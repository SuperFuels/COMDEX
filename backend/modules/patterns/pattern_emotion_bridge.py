from typing import Union

from backend.modules.patterns.pattern_registry import PatternRegistry
from backend.modules.creative.symbolic_mutation_engine import SymbolicMutationEngine

class PatternEmotionBridge:
    """
    Bridges pattern detection with emotion-based modulation and creative response.
    """

    def __init__(self):
        self.registry = PatternRegistry()
        self.mutator = SymbolicMutationEngine()

    def inject_emotional_response(self, pattern_id: Union[str, dict], emotion_state: dict) -> dict:
        # 🔧 FIX: Accept pattern_id as str or dict and extract if needed
        if isinstance(pattern_id, dict):
            pattern_id = pattern_id.get("id")

        pattern = self.registry.get(pattern_id)
        if not pattern:
            return {"error": "Pattern not found."}

        emotion = emotion_state.get("emotion", "")
        if emotion in ["curious", "confused", "inspired"]:
            mutated = self.mutator.mutate_from_pattern(pattern.to_dict())
            return {
                "emotion": emotion,
                "mutated_pattern": mutated,
                "reason": f"Emotion '{emotion}' triggered pattern adaptation"
            }

        return {"info": f"No emotional mutation triggered for emotion '{emotion}'."}

def trigger_emotion_from_pattern(pattern_id: Union[str, dict], emotion_state: dict) -> dict:
    bridge = PatternEmotionBridge()
    return bridge.inject_emotional_response(pattern_id, emotion_state)