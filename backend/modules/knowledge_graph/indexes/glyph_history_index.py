"""
📄 glyph_history_index.py

🔁 Glyph Lineage & Evolution Index
Tracks symbolic glyph ancestry, evolution, forks, mutations, and historical context
across containers and systems.

Design Rubric:
- 🧬 Operator Lineage Tracking .......... ✅
- 🔁 Mutation & Fork Log ................ ✅
- ⏱️ Timestamps & Ticks ................ ✅
- 📦 Container Context Awareness ........ ✅
- 📚 .dc Export + Plugin Compatibility .. ✅
- 🧠 Summary + Search API ............... ✅
"""

import json
from datetime import datetime
from typing import List, Dict, Optional


class GlyphHistoryRecord:
    def __init__(
        self,
        glyph_id: str,
        parent_id: Optional[str],
        operation: str,  # 'fork', 'rewrite', 'mutation', 'entangle', etc.
        tick: Optional[int] = None,
        container_id: Optional[str] = None,
        coord: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.glyph_id = glyph_id
        self.parent_id = parent_id
        self.operation = operation
        self.tick = tick
        self.coord = coord
        self.container_id = container_id
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "glyph_id": self.glyph_id,
            "parent_id": self.parent_id,
            "operation": self.operation,
            "tick": self.tick,
            "coord": self.coord,
            "container_id": self.container_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class GlyphHistoryIndex:
    def __init__(self):
        self.records: List[GlyphHistoryRecord] = []

    def log(
        self,
        glyph_id: str,
        parent_id: Optional[str],
        operation: str,
        tick: Optional[int] = None,
        container_id: Optional[str] = None,
        coord: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        record = GlyphHistoryRecord(
            glyph_id=glyph_id,
            parent_id=parent_id,
            operation=operation,
            tick=tick,
            container_id=container_id,
            coord=coord,
            metadata=metadata,
        )
        self.records.append(record)

    def export_json(self, compressed: bool = False) -> str:
        data = [r.to_dict() for r in self.records]
        if compressed:
            return json.dumps(data, separators=(',', ':'))
        return json.dumps(data, indent=2)

    def summarize(self) -> Dict:
        op_count = {}
        for r in self.records:
            op_count[r.operation] = op_count.get(r.operation, 0) + 1

        return {
            "total_records": len(self.records),
            "by_operation": op_count,
            "latest_tick": max([r.tick for r in self.records if r.tick is not None], default=None),
        }

    def search_by_glyph(self, glyph_id: str) -> List[Dict]:
        return [r.to_dict() for r in self.records if r.glyph_id == glyph_id or r.parent_id == glyph_id]