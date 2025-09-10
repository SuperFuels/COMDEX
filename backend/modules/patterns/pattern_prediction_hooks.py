from typing import List, Dict, Optional
import random

from backend.modules.patterns.pattern_registry import PatternRegistry
from backend.modules.patterns.pattern_websocket_broadcast import PatternWebSocketBroadcaster


class PatternPredictionHooks:
    """
    Suggests likely next glyphs or pattern completions based on current glyph sequence.
    Integrates with PredictionEngine or live mutation handlers.
    """

    def __init__(self):
        self.registry = PatternRegistry()
        self.broadcaster = PatternWebSocketBroadcaster()

    def suggest_next_glyphs(self, current_glyphs: List[str], limit: int = 5) -> List[Dict]:
        """
        Returns a list of pattern-based glyph predictions that might follow the given glyphs.
        """
        suggestions = []
        seen: set = set()

        for pattern in self.registry.get_all():
            pattern_glyphs = getattr(pattern, "glyphs", [])
            if self._matches_partial(pattern_glyphs, current_glyphs):
                next_glyph = self._next_symbol_after(pattern_glyphs, current_glyphs)
                if next_glyph and next_glyph not in seen:
                    suggestions.append({
                        "pattern_id": pattern.get("pattern_id"),
                        "name": pattern.get("name"),
                        "next_glyph": next_glyph,
                        "sqi_score": pattern.get("sqi_score", 0.0),
                        "prediction_trace": pattern_glyphs,
                        "type": pattern.get("type", "unknown")
                    })
                    seen.add(next_glyph)

        return sorted(suggestions, key=lambda s: s["sqi_score"], reverse=True)[:limit]

    def predict_from_context(self, context: Dict[str, str], current_glyphs: List[str]) -> List[str]:
        """
        Advanced context-aware glyph prediction — e.g., based on goal, emotion, or state.
        """
        goal = context.get("goal", "").lower()
        emotion = context.get("emotion", "").lower()

        matching_patterns = self.registry.query_patterns_by_context(goal=goal, emotion=emotion)
        candidates = []

        for pattern in matching_patterns:
            pattern_glyphs = pattern.get("glyphs", [])
            if self._matches_partial(pattern_glyphs, current_glyphs):
                next_g = self._next_symbol_after(pattern_glyphs, current_glyphs)
                if next_g:
                    candidates.append((next_g, pattern.get("sqi_score", 0.0)))

        sorted_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)
        return [g for g, _ in sorted_candidates[:5]]

    def _matches_partial(self, pattern_glyphs: List[str], prefix: List[str]) -> bool:
        """
        Checks if the pattern starts with the given glyph sequence.
        """
        if not prefix:
            return False
        return pattern_glyphs[:len(prefix)] == prefix

    def _next_symbol_after(self, pattern_glyphs: List[str], prefix: List[str]) -> Optional[str]:
        """
        Returns the glyph immediately after the prefix in the pattern, if available.
        """
        if len(prefix) >= len(pattern_glyphs):
            return None
        return pattern_glyphs[len(prefix)]

    def broadcast_predictions(self, glyph: str, current_sequence: List[str]):
        """
        Broadcast predicted glyph completions over WebSocket.
        """
        predictions = self.suggest_next_glyphs(current_sequence)
        self.broadcaster.broadcast_pattern_prediction(glyph, predictions)