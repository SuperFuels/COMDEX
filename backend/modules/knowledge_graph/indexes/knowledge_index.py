# File: backend/modules/knowledge_graph/knowledge_index.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Optional, Set
import hashlib
import json
import os
import threading

# 🔔 Toggle: auto-emit debounced SQI bus event when an entry is added
KG_EMIT_ON_ADD = os.getenv("KG_EMIT_ON_ADD", "true").lower() == "true"


class KnowledgeIndex:
    def __init__(self, max_entries: int = 100_000):
        # In-memory store (ring-buffer-ish with pruning) + O(1) dedupe set
        self.entries: List[Dict] = []
        self._seen: Set[str] = set()
        self._lock = threading.RLock()
        self._max = max_entries

        # NEW: edge store (set for dedupe), plus cached list view
        # Directed edges: (src, dst, relation)
        self._edge_set: Set[tuple] = set()
        self._edge_list: List[Dict] = []  # [{ "src": ..., "dst": ..., "relation": ... }]

    # -----------------------
    # Public API
    # -----------------------
    def add_entry(
        self,
        glyph: str,
        meaning: str,
        tags: List[str],
        source: str,
        container_id: str,
        confidence: float = 1.0,
        plugin: Optional[str] = None,
        anchor: Optional[Dict] = None,
        external_hash: Optional[str] = None,   # allow bus-provided hash (idempotency)
        timestamp: Optional[str] = None        # allow external timestamp
    ) -> bool:
        """
        Add a new knowledge entry.
        Returns True if inserted, False if deduped (or only merged).
        """
        entry = {
            "glyph": glyph,
            "meaning": meaning,
            "tags": tags or [],
            "source": source,
            "container_id": container_id,
            "confidence": float(confidence),
            "timestamp": self._normalize_ts(timestamp),
        }
        if plugin:
            entry["plugin"] = plugin
        if anchor:
            entry["anchor"] = {
                "env_obj_id": anchor.get("env_obj_id"),
                "type": anchor.get("type"),
                "coord": anchor.get("coord", {}),
            }

        # Prefer external hash when provided (e.g., from event bus)
        h = external_hash or self._hash_entry(entry)

        with self._lock:
            if h in self._seen:
                # Optional upsert-on-duplicate: merge richer info
                existing = self.get_by_hash(h)
                if existing is not None:
                    # Union tags and keep max confidence
                    existing["tags"] = sorted(set(existing.get("tags", [])) | set(tags or []))
                    existing["confidence"] = max(existing.get("confidence", 0.0), float(confidence))
                    # Keep earliest timestamp by default; comment next line to always prefer latest
                    # existing["timestamp"] = min(existing["timestamp"], entry["timestamp"])
                return False

            entry["_hash"] = h
            self.entries.append(entry)
            self._seen.add(h)

            # Simple prune when exceeding cap (FIFO)
            if len(self.entries) > self._max:
                old = self.entries.pop(0)
                oh = old.get("_hash")
                if oh:
                    self._seen.discard(oh)
                    # Also drop any edges that referenced the evicted node
                    self._drop_edges_touching(oh)

            # 🔔 Auto-emit debounced SQI event so downstream listeners (KG ingest, GHX, etc) see it
            if KG_EMIT_ON_ADD:
                try:
                    # Lazy import to avoid circular imports at module load
                    from backend.modules.sqi.sqi_event_bus import publish_kg_added
                    payload = {
                        "container_id": container_id,
                        "entry": {
                            # Use anchor env_obj_id if present as a human-ish id; optional
                            "id": entry.get("anchor", {}).get("env_obj_id") if entry.get("anchor") else None,
                            "hash": h,  # idempotency key matching sqi_event_bus debounce
                            # best-effort event type; if you have a dedicated type, replace this
                            "type": source,
                            "timestamp": entry["timestamp"],
                            "tags": entry.get("tags", []),
                            "plugin": entry.get("plugin"),
                            # Callers that want relations attach them via the bus payload meta
                        },
                    }
                    publish_kg_added(payload)
                except Exception:
                    # Telemetry should never break core writes
                    pass

            return True

    def get_by_hash(self, h: str) -> Optional[Dict]:
        # Linear scan is fine for moderate sizes; index if you need speed
        return next((e for e in self.entries if e.get("_hash") == h), None)

    def search(self, tag: Optional[str] = None, container_id: Optional[str] = None) -> List[Dict]:
        with self._lock:
            data = self.entries
            if tag:
                data = [e for e in data if tag in e.get("tags", [])]
            if container_id:
                data = [e for e in data if e.get("container_id") == container_id]
            return list(data)

    def get_recent(self, n: int = 10, container_id: Optional[str] = None) -> List[Dict]:
        with self._lock:
            data = self.entries if container_id is None else [e for e in self.entries if e["container_id"] == container_id]
            return sorted(data, key=lambda e: e["timestamp"], reverse=True)[:n]

    def to_dict(self) -> Dict:
        with self._lock:
            return {
                "type": "KnowledgeIndex",
                "total_entries": len(self.entries),
                "entries": list(self.entries),
                "edges": list(self._edge_list),  # expose links too
            }

    # -----------------------
    # Graph Links (Edges)
    # -----------------------
    def add_link(self, src_hash: str, dst_hash: str, relation: str = "relates_to") -> bool:
        if not src_hash or not dst_hash:
            return False
        # normalize
        src = str(src_hash)
        dst = str(dst_hash)
        rel = str(relation or "relates_to")
        key = (src, dst, rel)
        with self._lock:
            # Only allow links between known nodes
            if src not in self._seen or dst not in self._seen:
                return False
            if key in self._edge_set:
                return False
            self._edge_set.add(key)
            self._edge_list.append({"src": src, "dst": dst, "relation": rel})
            return True

    def edges(self) -> List[Dict]:
        with self._lock:
            return list(self._edge_list)

    def get_links_for(self, h: str) -> List[Dict]:
        if not h:
            return []
        with self._lock:
            return [e for e in self._edge_list if e["src"] == h or e["dst"] == h]

    # -----------------------
    # Persistence (dev-friendly)
    # -----------------------
    def dump(self, path: str) -> None:
        with self._lock:
            blob = {
                "entries": self.entries,
                "edges": list(self._edge_list),   # NEW
            }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(blob, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", [])
        edges = data.get("edges", [])  # NEW
        with self._lock:
            self.entries = entries
            self._seen = {e.get("_hash") for e in self.entries if e.get("_hash")}
            # rebuild edge stores
            self._edge_list = []
            self._edge_set = set()
            for e in edges:
                src = e.get("src")
                dst = e.get("dst")
                rel = e.get("relation", "relates_to")
                if src and dst:
                    key = (src, dst, rel)
                    if key not in self._edge_set:
                        # Only restore links that reference known nodes
                        if src in self._seen and dst in self._seen:
                            self._edge_set.add(key)
                            self._edge_list.append({"src": src, "dst": dst, "relation": rel})

    # -----------------------
    # Internals
    # -----------------------
    def _hash_entry(self, entry: Dict) -> str:
        # Core idempotency key: stable across replays within same container
        base = f"{entry['glyph']}|{entry['meaning']}|{entry['container_id']}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _normalize_ts(self, ts: Optional[str]) -> str:
        """
        Normalize timestamps to RFC3339 UTC with 'Z'.
        Accepts None, '...Z', or ISO8601 with offsets.
        """
        if not ts:
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            if ts.endswith("Z"):
                # Best-effort: ensure it's valid ISO; if not, fall back to now
                _ = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return ts
            return (
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
                .astimezone(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
        except Exception:
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _drop_edges_touching(self, h: str) -> None:
        """Remove any edges that reference an evicted node."""
        # assumes lock is already held
        if not self._edge_list:
            return
        keep_list: List[Dict] = []
        keep_set: Set[tuple] = set()
        for e in self._edge_list:
            if e["src"] == h or e["dst"] == h:
                continue
            key = (e["src"], e["dst"], e["relation"])
            keep_list.append(e)
            keep_set.add(key)
        self._edge_list = keep_list
        self._edge_set = keep_set


# Global instance
knowledge_index = KnowledgeIndex()