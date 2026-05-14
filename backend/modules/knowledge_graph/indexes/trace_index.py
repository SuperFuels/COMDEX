"""
📄 trace_index.py

⧖ Collapse & Execution Trace Index
Tracks symbolic glyph execution events (collapse, entanglement, rewrite, etc.)
with full metadata for introspection, cost estimation, and replay systems.

Design Rubric:
- ⧖ Collapse Event Tracking ............. ✅
- ↔ Entangled Glyph Awareness ............ ✅
- 📊 Cost / Bias / Entropy Recording ..... ✅
- 🧠 Source Attribution (Codex, Tessaris) ✅
- 🔄 Fork + Trace ID + Replay Hooks ...... ✅
- 📦 Container Injection Compatibility ... ✅
- 📚 Replay-Compatible JSON Export ....... ✅
"""

import json
from datetime import datetime
from typing import List, Dict, Optional


class TraceEvent:
    def __init__(
        self,
        glyph: str,
        op: str,
        tick: int,
        cost: float,
        bias: Optional[float] = None,
        source: Optional[str] = None,
        container_id: Optional[str] = None,
        entropy: Optional[float] = None,
        fork_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        replay_id: Optional[str] = None,
    ):
        self.glyph = glyph
        self.op = op  # collapse (⧖), entangle (↔), rewrite (⬁), etc.
        self.tick = tick
        self.cost = cost
        self.bias = bias
        self.source = source  # e.g., "CodexExecutor"
        self.container_id = container_id
        self.entropy = entropy
        self.fork_id = fork_id
        self.trace_id = trace_id
        self.replay_id = replay_id
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "glyph": self.glyph,
            "op": self.op,
            "tick": self.tick,
            "cost": self.cost,
            "bias": self.bias,
            "source": self.source,
            "container_id": self.container_id,
            "entropy": self.entropy,
            "fork_id": self.fork_id,
            "trace_id": self.trace_id,
            "replay_id": self.replay_id,
            "timestamp": self.timestamp,
        }


class TraceIndex:
    def __init__(self):
        self.events: List[TraceEvent] = []

    def add_event(self, event: TraceEvent):
        self.events.append(event)

    def to_json(self, compressed: bool = False) -> str:
        data = [e.to_dict() for e in self.events]
        return json.dumps(data, separators=(',', ':')) if compressed else json.dumps(data, indent=2)

    def summarize(self) -> Dict:
        return {
            "total_events": len(self.events),
            "avg_cost": sum([e.cost for e in self.events]) / len(self.events) if self.events else 0,
            "by_op": self._op_counts(),
        }

    def _op_counts(self) -> Dict[str, int]:
        counts = {}
        for e in self.events:
            counts[e.op] = counts.get(e.op, 0) + 1
        return counts


def inject_trace_event(container: Dict, event: Dict):
    """
    Injects a symbolic trace event into the container's 'trace' stream.
    """
    if "trace" not in container:
        container["trace"] = []
    container["trace"].append(event)