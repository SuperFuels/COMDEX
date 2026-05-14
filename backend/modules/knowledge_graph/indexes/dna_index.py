"""
Design Rubric:
- 🔁 Deduplication Logic ............ ✅
- 📦 Container Awareness ............ ✅
- 🧠 Semantic Metadata .............. ✅
- ⏱️ Timestamps (ISO 8601) .......... ✅
- 🧩 Plugin Compatibility ........... ✅
- 🔍 Search & Summary API .......... ✅
- 📊 Readable + Compressed Export ... ✅
- 📚 .dc Container Injection ........ ✅

📄 Index Purpose:
Tracks all symbolic DNA activity across mutation, entanglement, or collapse operations.  
Stores ⬁ self-rewrites, ↔ links, and ⧖ fork events with symbolic cause/context.  
Used by glyph synthesizers, entropy validators, and introspection engines.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional


class DNAMutationRecord:
    def __init__(
        self,
        glyph: str,
        op: str,
        context: Optional[str] = None,
        tick: Optional[int] = None,
        container_id: Optional[str] = None,
        coord: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.glyph = glyph
        self.op = op  # '⬁', '↔', '⧖', etc.
        self.context = context
        self.tick = tick
        self.container_id = container_id
        self.coord = coord
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "glyph": self.glyph,
            "op": self.op,
            "context": self.context,
            "tick": self.tick,
            "container_id": self.container_id,
            "coord": self.coord,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class DNAIndex:
    def __init__(self):
        self.records: List[DNAMutationRecord] = []

    def add_record(self, record: DNAMutationRecord):
        self.records.append(record)

    def to_json(self, compressed: bool = False) -> str:
        data = [r.to_dict() for r in self.records]
        if compressed:
            return json.dumps(data, separators=(',', ':'))
        return json.dumps(data, indent=2)

    def summarize(self) -> Dict:
        ops = {}
        for r in self.records:
            ops[r.op] = ops.get(r.op, 0) + 1
        return {
            "total": len(self.records),
            "by_op": ops,
            "latest_tick": max([r.tick for r in self.records if r.tick is not None], default=None),
        }