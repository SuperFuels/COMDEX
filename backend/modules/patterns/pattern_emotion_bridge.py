# File: backend/modules/patterns/pattern_emotion_bridge.py

from typing import Union, Dict, Any, List
from backend.modules.patterns.pattern_registry import PatternRegistry
from backend.modules.creative.symbolic_mutation_engine import SymbolicMutationEngine

class PatternEmotionBridge:
    """
    Bridges symbolic pattern detection with emotional response logic.
    Based on the current emotion state, may trigger mutation, reinforcement,
    or collapse of symbolic patterns.
    """

    def __init__(self):
        self.registry = PatternRegistry()
        self.mutator = SymbolicMutationEngine()

    def inject_emotional_response(self, pattern_id: Union[str, Dict[str, Any]], emotion_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Respond to an emotion linked to a pattern by mutating or modulating it.

        Args:
            pattern_id: Pattern ID string or pattern dict with 'id'
            emotion_state: Dict with at least 'emotion' key (e.g., {"emotion": "curious"})

        Returns:
            Dict with mutation or info message
        """
        pid = pattern_id.get("id") if isinstance(pattern_id, dict) else pattern_id
        pattern = self.registry.get(pid)
        if not pattern:
            return {"error": f"Pattern not found: {pid}"}

        emotion = emotion_state.get("emotion", "").lower()
        if not emotion:
            return {"error": "No emotion provided."}

        # Emotion-based mutation strategy
        if emotion in {"curious", "confused", "inspired", "playful"}:
            mutated = self.mutator.mutate_from_pattern(pattern.to_dict())
            return {
                "emotion": emotion,
                "action": "mutated",
                "mutated_pattern": mutated,
                "reason": f"Emotion '{emotion}' triggered exploration mutation."
            }

        elif emotion in {"fear", "grief", "regret"}:
            collapsed = self.mutator.collapse_pattern(pattern.to_dict())
            return {
                "emotion": emotion,
                "action": "collapsed",
                "collapsed_pattern": collapsed,
                "reason": f"Emotion '{emotion}' triggered pattern collapse."
            }

        elif emotion in {"joy", "gratitude", "hope"}:
            reinforced = self.mutator.reinforce_pattern(pattern.to_dict())
            return {
                "emotion": emotion,
                "action": "reinforced",
                "reinforced_pattern": reinforced,
                "reason": f"Emotion '{emotion}' triggered reinforcement."
            }

        return {
            "emotion": emotion,
            "action": "none",
            "info": f"No symbolic modulation mapped for emotion '{emotion}'."
        }

    def respond_to_multiple_patterns(self, pattern_ids: List[Union[str, Dict[str, Any]]], emotion_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply emotional response to a list of patterns.
        """
        results = []
        for pid in pattern_ids:
            result = self.inject_emotional_response(pid, emotion_state)
            results.append(result)
        return results


# Optional direct trigger function
def trigger_emotion_from_pattern(pattern_id: Union[str, dict], emotion_state: Dict[str, Any]) -> Dict[str, Any]:
    bridge = PatternEmotionBridge()
    return bridge.inject_emotional_response(pattern_id, emotion_state)


# Singleton instance if needed
pattern_emotion_bridge = PatternEmotionBridge()