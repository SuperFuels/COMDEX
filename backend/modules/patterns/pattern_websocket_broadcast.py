# pattern_websocket_broadcast.py
# Location: backend/modules/patterns/

from typing import Dict, List, Optional, Any
from backend.modules.patterns.pattern_registry import Pattern
from backend.modules.codex.codex_websocket_interface import send_codex_ws_event_sync as send_codex_ws_event


class PatternWebSocketBroadcaster:
    """
    Broadcasts symbolic pattern events to the frontend Codex HUD via WebSocket.
    Supports real-time detection, mutation, prediction, and trace replay overlays.
    """

    def __init__(self):
        self.topic = "pattern_event"

    def broadcast_pattern_detected(self, pattern: Pattern, container_id: str = ""):
        """
        Emit WebSocket message for a detected symbolic pattern.
        """
        payload = {
            "subtype": "pattern_detected",
            "pattern": self._serialize_pattern(pattern, container_id)
        }
        send_codex_ws_event(self.topic, payload)

    def broadcast_pattern_mutated(self, mutated_pattern: Dict[str, Any], origin_pattern_id: str = "", container_id: str = ""):
        """
        Emit WebSocket message when a symbolic pattern undergoes mutation.
        """
        payload = {
            "subtype": "pattern_mutated",
            "origin_pattern_id": origin_pattern_id,
            "mutation_type": mutated_pattern.get("mutation_strategy", "unknown"),
            "pattern": mutated_pattern,
            "container_id": container_id
        }
        send_codex_ws_event(self.topic, payload)

    def broadcast_pattern_prediction(self, glyph: str, suggested_patterns: List[Dict[str, Any]]):
        """
        Emit WebSocket message containing predicted pattern completions for a glyph.
        """
        payload = {
            "subtype": "pattern_prediction",
            "glyph": glyph,
            "suggestions": suggested_patterns
        }
        send_codex_ws_event(self.topic, payload)

    def broadcast_pattern_trace(self, pattern_id: str, trace_data: Dict[str, Any]):
        """
        Emit WebSocket message for replaying a previously executed pattern trace.
        """
        payload = {
            "subtype": "pattern_trace",
            "pattern_id": pattern_id,
            "trace": trace_data
        }
        send_codex_ws_event(self.topic, payload)

    def broadcast_pattern_match(self, pattern: Dict[str, Any], container_id: Optional[str] = None):
        """
        Emit WebSocket message for a matched pattern in a live container.
        """
        payload = {
            "subtype": "pattern_match",
            "pattern_id": pattern.get("pattern_id"),
            "name": pattern.get("name"),
            "glyphs": pattern.get("glyphs", []),
            "type_tag": pattern.get("type", ""),
            "sqi_score": pattern.get("sqi_score"),
            "trigger_logic": pattern.get("trigger_logic"),
            "prediction": pattern.get("prediction"),
            "source_container": pattern.get("source_container"),
            "container_id": container_id,
        }
        send_codex_ws_event(self.topic, payload)

    def _serialize_pattern(self, pattern: Pattern, container_id: str = "") -> Dict[str, Any]:
        return {
            "pattern_id": pattern.pattern_id,
            "name": pattern.name,
            "glyphs": pattern.glyphs,
            "type": pattern.type,
            "trigger_logic": pattern.trigger_logic,
            "sqi_score": pattern.sqi_score,
            "prediction": pattern.prediction,
            "source_container": container_id or pattern.source_container,
        }