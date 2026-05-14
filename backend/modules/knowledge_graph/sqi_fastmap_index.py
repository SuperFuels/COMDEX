# backend/modules/knowledge_graph/sqi_fastmap_index.py

import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any

FASTMAP_INDEX_PATH = "data/fastmap_index.json"
LOCK = threading.Lock()

class SQIFastMapIndex:
    def __init__(self, path: str = FASTMAP_INDEX_PATH):
        self.index_path = path
        self.entries: Dict[str, dict] = {}
        self.inverse_index: Dict[str, List[str]] = {}
        self.load_from_disk()

    def add_or_update_entry(self, container_id: str, topic_vector: List[str], metadata: dict):
        with LOCK:
            # Flags derived from metadata
            collapsed = metadata.get("default_state", "expanded") == "collapsed"
            attention = metadata.get("attention", "")
            has_links = bool(metadata.get("entangled_links") or metadata.get("linkPreview"))

            state_flags = list(set(metadata.get("state_flags", [])))
            if collapsed and "collapsed" not in state_flags:
                state_flags.append("collapsed")
            if attention == "high" and "hot" not in state_flags:
                state_flags.append("hot")
            if has_links and "linked" not in state_flags:
                state_flags.append("linked")

            self.entries[container_id] = {
                "topic_vector": topic_vector,
                "active_links": metadata.get("active_links", []),
                "collapsed_state": "collapsed" if collapsed else "expanded",
                "last_update": metadata.get("last_update") or datetime.utcnow().isoformat(),
                "state_flags": state_flags,
                "keywords": metadata.get("keywords", []),
                "ancestry": metadata.get("glyph_lineage", []),
                "ghx_hint": metadata.get("ghx_hint", None),
                "layout_type": metadata.get("layout_type", None),
                "hover_summary": metadata.get("hover_summary", None)
            }

            for keyword in topic_vector + metadata.get("keywords", []) + metadata.get("glyph_lineage", []):
                self.inverse_index.setdefault(keyword.lower(), [])
                if container_id not in self.inverse_index[keyword.lower()]:
                    self.inverse_index[keyword.lower()].append(container_id)

            self.serialize_to_disk()

    def get_state(self, container_id: str) -> Optional[dict]:
        return self.entries.get(container_id)

    def set_collapsed_state(self, container_id: str, state: str):
        with LOCK:
            if container_id in self.entries:
                self.entries[container_id]["collapsed_state"] = state
                self.entries[container_id]["last_update"] = datetime.utcnow().isoformat()
                self.serialize_to_disk()

    def mark_as_archived(self, container_id: str):
        with LOCK:
            if container_id in self.entries:
                flags = self.entries[container_id].setdefault("state_flags", [])
                if "archived" not in flags:
                    flags.append("archived")
                self.entries[container_id]["last_update"] = datetime.utcnow().isoformat()
                self.serialize_to_disk()

    def query_by_keyword(self, keyword: str) -> List[str]:
        return self.inverse_index.get(keyword.lower(), [])

    def serialize_to_disk(self):
        try:
            with open(self.index_path, "w") as f:
                json.dump({
                    "entries": self.entries,
                    "inverse_index": self.inverse_index
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save FastMap index: {e}")

    def load_from_disk(self):
        if not os.path.exists(self.index_path):
            return
        try:
            with open(self.index_path, "r") as f:
                data = json.load(f)
                self.entries = data.get("entries", {})
                self.inverse_index = data.get("inverse_index", {})
        except Exception as e:
            print(f"⚠️ Failed to load FastMap index: {e}")


# Singleton instance
sqi_fastmap = SQIFastMapIndex()