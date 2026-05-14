"""
📄 external_agent_index.py

🌐 External Agent Interaction Index
Tracks symbolic glyph interactions by external agents (human, AI, system, remote peer).
Used for identity tracking, shared cognition, and cross-agent memory logging.

Design Rubric:
- 🧠 Agent ID / Identity Attribution ........ ✅
- 📩 Glyph Intent + Context Metadata ........ ✅
- 📦 Container Awareness ..................... ✅
- ⏱️ Tick + Timestamp Tracking .............. ✅
- 🧩 Plugin & .dc Container Integration ...... ✅
- 📊 Interaction Summary API ................ ✅
"""

import json
from datetime import datetime
from typing import List, Dict, Optional


class ExternalAgentInteraction:
    def __init__(
        self,
        agent_id: str,
        glyph: str,
        intent: Optional[str] = None,
        context: Optional[str] = None,
        tick: Optional[int] = None,
        container_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.agent_id = agent_id  # UUID or symbolic name
        self.glyph = glyph
        self.intent = intent
        self.context = context
        self.tick = tick
        self.container_id = container_id
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "glyph": self.glyph,
            "intent": self.intent,
            "context": self.context,
            "tick": self.tick,
            "container_id": self.container_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class ExternalAgentIndex:
    def __init__(self):
        self.interactions: List[ExternalAgentInteraction] = []

    def add_interaction(self, record: ExternalAgentInteraction):
        self.interactions.append(record)

    def to_json(self, compressed: bool = False) -> str:
        data = [i.to_dict() for i in self.interactions]
        return json.dumps(data, separators=(',', ':')) if compressed else json.dumps(data, indent=2)

    def summarize(self) -> Dict:
        agent_counts = {}
        for i in self.interactions:
            agent_counts[i.agent_id] = agent_counts.get(i.agent_id, 0) + 1
        return {
            "total_interactions": len(self.interactions),
            "by_agent": agent_counts,
            "latest_tick": max([i.tick for i in self.interactions if i.tick is not None], default=None),
        }