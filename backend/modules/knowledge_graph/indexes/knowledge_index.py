# backend/modules/knowledge_graph/knowledge_index.py

from datetime import datetime
from typing import List, Dict, Optional
import hashlib

class KnowledgeIndex:
    def __init__(self):
        self.entries: List[Dict] = []

    def add_entry(
        self,
        glyph: str,
        meaning: str,
        tags: List[str],
        source: str,
        container_id: str,
        confidence: float = 1.0,
        plugin: Optional[str] = None,
        anchor: Optional[Dict] = None  # ✅ NEW: Anchor support
    ):
        """
        Add a new knowledge entry with optional anchor metadata.
        """
        entry = {
            "glyph": glyph,
            "meaning": meaning,
            "tags": tags,
            "source": source,
            "container_id": container_id,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if plugin:
            entry["plugin"] = plugin
        if anchor:
            entry["anchor"] = {
                "env_obj_id": anchor.get("env_obj_id"),
                "type": anchor.get("type"),
                "coord": anchor.get("coord", {})
            }

        # Deduplicate by glyph + meaning + container_id
        hash_key = self._hash_entry(entry)
        if not any(e.get("_hash") == hash_key for e in self.entries):
            entry["_hash"] = hash_key
            self.entries.append(entry)

    def _hash_entry(self, entry: Dict) -> str:
        base = f"{entry['glyph']}|{entry['meaning']}|{entry['container_id']}"
        return hashlib.sha256(base.encode()).hexdigest()

    def search(self, tag: str) -> List[Dict]:
        return [e for e in self.entries if tag in e.get("tags", [])]

    def get_recent(self, n: int = 10) -> List[Dict]:
        return sorted(self.entries, key=lambda e: e["timestamp"], reverse=True)[:n]

    def to_dict(self) -> Dict:
        return {
            "type": "KnowledgeIndex",
            "total_entries": len(self.entries),
            "entries": self.entries
        }

    def summary(self) -> Dict:
        tags = [tag for e in self.entries for tag in e.get("tags", [])]
        unique_tags = list(set(tags))
        return {
            "total_glyphs": len(self.entries),
            "unique_tags": unique_tags,
            "average_confidence": round(sum(e["confidence"] for e in self.entries) / len(self.entries), 3) if self.entries else 0.0,
            "sources": list(set(e["source"] for e in self.entries))
        }

# Global instance
knowledge_index = KnowledgeIndex()