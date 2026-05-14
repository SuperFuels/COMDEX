# File: backend/modules/patterns/pattern_trace_engine.py

import os
import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

# ✅ Trace log directory
TRACE_LOG_DIR = "data/traces"
os.makedirs(TRACE_LOG_DIR, exist_ok=True)

# Optional: sync to GHX
try:
    from backend.modules.ghx.ghx_replay_broadcast import emit_pattern_timeline_event
except ImportError:
    emit_pattern_timeline_event = None

# Optional: inject into Knowledge Graph
try:
    from backend.modules.knowledge.knowledge_graph_writer import inject_pattern_timeline
except ImportError:
    inject_pattern_timeline = None


class PatternTraceEngine:
    """
    Tracks symbolic pattern activations, mutations, collapses,
    and emotion-based tags for GHX/QFC/KG timelines or reflection.
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
        Records a symbolic event in the timeline for a specific container.
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "pattern": pattern_signature,
            "event_type": event_type,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }

        self._timeline.setdefault(container_id, []).append(event)

        # 🔁 Emit to GHX if available
        if emit_pattern_timeline_event:
            emit_pattern_timeline_event(container_id, event)

        # 🧠 Inject into Knowledge Graph if enabled
        if inject_pattern_timeline:
            inject_pattern_timeline(container_id, event)

        return event

    def get_timeline(self, container_id: str) -> List[Dict[str, Any]]:
        """
        Return the full symbolic event timeline for a given container.
        """
        return self._timeline.get(container_id, [])

    def clear_timeline(self, container_id: Optional[str] = None):
        """
        Clears the timeline either for a specific container or globally.
        """
        if container_id:
            self._timeline.pop(container_id, None)
        else:
            self._timeline.clear()

    def collapse_event(
        self,
        container_id: str,
        pattern_signature: str,
        sqi_before: float,
        sqi_after: float
    ) -> Dict[str, Any]:
        """
        Logs a collapse or evolution event based on SQI delta.
        """
        delta = round(sqi_after - sqi_before, 4)
        event_type = "collapse" if delta < -0.05 else "evolution"
        metadata = {
            "sqi_before": sqi_before,
            "sqi_after": sqi_after,
            "delta": delta,
        }
        return self.trace_event(container_id, pattern_signature, event_type, metadata)

    def mutation_event(
        self,
        container_id: str,
        pattern_signature: str,
        mutation_type: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Records a mutation event with metadata about the mutation type.
        """
        metadata = {"mutation_type": mutation_type, **details}
        return self.trace_event(container_id, pattern_signature, "mutation", metadata)

    def activation_event(
        self,
        container_id: str,
        pattern_signature: str,
        trigger_source: str,
        glyph_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Records a pattern activation event from a trigger source and related glyphs.
        """
        metadata = {
            "trigger": trigger_source,
            "glyph_ids": glyph_ids,
        }
        return self.trace_event(container_id, pattern_signature, "activation", metadata)

    def emotional_tag(
        self,
        container_id: str,
        pattern_signature: str,
        emotion: str,
        intensity: float
    ) -> Dict[str, Any]:
        """
        Adds an emotional tag to a pattern on the timeline.
        """
        metadata = {
            "emotion": emotion,
            "intensity": round(intensity, 3),
        }
        return self.trace_event(container_id, pattern_signature, "emotion_tag", metadata)


def record_trace(cell_id: str, message: str) -> None:
    """
    🧠 Append a symbolic trace log entry for a specific cell.
    Writes to: data/traces/{cell_id}.trace.json
    """
    log_path = os.path.join(TRACE_LOG_DIR, f"{cell_id}.trace.json")

    # Load existing trace log if it exists and is valid JSON
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            try:
                trace_log = json.load(f)
            except json.JSONDecodeError:
                trace_log = []
    else:
        trace_log = []

    # Append new message entry
    trace_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": message,
    }

    trace_log.append(trace_entry)

    # Save to disk
    with open(log_path, "w") as f:
        json.dump(trace_log, f, indent=2)

    print(f"[Trace] {cell_id}: {message}")


# ✅ Global singleton instance
pattern_trace_engine = PatternTraceEngine()