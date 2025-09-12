# File: backend/modules/patterns/pattern_trace_engine.py

from typing import List, Dict, Any, Optional
import time
import uuid

# Optional: sync to GHX or KG
try:
    from backend.modules.ghx.ghx_replay_broadcast import emit_pattern_timeline_event
except ImportError:
    emit_pattern_timeline_event = None

# Optional: store in KG or logs
try:
    from backend.modules.knowledge.knowledge_graph_writer import inject_pattern_timeline
except ImportError:
    inject_pattern_timeline = None


class PatternTraceEngine:
    """
    Tracks symbolic pattern activations, collapses, mutations,
    and timeline tagging for GHX, KG, or CodexLang reflection.
    """

    def __init__(self):
        self._timeline: Dict[str, List[Dict[str, Any]]] = {}

    def trace_event(
        self,
        container_id: str,
        pattern_signature: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Records a pattern-related event on the timeline.
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "pattern": pattern_signature,
            "event_type": event_type,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }

        if container_id not in self._timeline:
            self._timeline[container_id] = []
        self._timeline[container_id].append(event)

        # Optional emit
        if emit_pattern_timeline_event:
            emit_pattern_timeline_event(container_id, event)

        # Optional KG logging
        if inject_pattern_timeline:
            inject_pattern_timeline(container_id, event)

        return event

    def get_timeline(self, container_id: str) -> List[Dict[str, Any]]:
        return self._timeline.get(container_id, [])

    def clear_timeline(self, container_id: Optional[str] = None):
        if container_id:
            self._timeline.pop(container_id, None)
        else:
            self._timeline.clear()

    def collapse_event(
        self, container_id: str, pattern_signature: str, sqi_before: float, sqi_after: float
    ):
        delta = round(sqi_after - sqi_before, 4)
        event_type = "collapse" if delta < -0.05 else "evolution"
        metadata = {
            "sqi_before": sqi_before,
            "sqi_after": sqi_after,
            "delta": delta,
        }
        return self.trace_event(container_id, pattern_signature, event_type, metadata)

    def mutation_event(
        self, container_id: str, pattern_signature: str, mutation_type: str, details: Dict[str, Any]
    ):
        metadata = {"mutation_type": mutation_type, **details}
        return self.trace_event(container_id, pattern_signature, "mutation", metadata)

    def activation_event(
        self, container_id: str, pattern_signature: str, trigger_source: str, glyph_ids: List[str]
    ):
        metadata = {
            "trigger": trigger_source,
            "glyph_ids": glyph_ids,
        }
        return self.trace_event(container_id, pattern_signature, "activation", metadata)

    def emotional_tag(
        self, container_id: str, pattern_signature: str, emotion: str, intensity: float
    ):
        metadata = {
            "emotion": emotion,
            "intensity": round(intensity, 3),
        }
        return self.trace_event(container_id, pattern_signature, "emotion_tag", metadata)


# Singleton instance
pattern_trace_engine = PatternTraceEngine()