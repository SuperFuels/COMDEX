from __future__ import annotations
from typing import Dict, Any, Tuple, Set, DefaultDict
from collections import defaultdict
from datetime import datetime

class KGWriterStub:
    """
    Minimal in-memory Knowledge Graph Writer.
    ✅ API-compatible with KnowledgeGraphWriter for testing/CLI mode.

    Provides:
    - upsert_container_node(meta) -> node_id
    - link(src, dst, rel, meta={})
    - inject_glyph(...)
    - write_scroll(scroll) -> node_id
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}     # node_id -> meta
        self.edges: Set[Tuple[str, str, str]] = set()  # (src, rel, dst)
        self.out: DefaultDict[str, Set[Tuple[str, str]]] = defaultdict(set)
        self.in_: DefaultDict[str, Set[Tuple[str, str]]] = defaultdict(set)

    def _node_id(self, meta: Dict[str, Any]) -> str:
        addr = (meta.get("meta") or {}).get("address") or meta.get("address")
        if isinstance(addr, str) and addr.strip():
            return addr
        node_id = meta.get("id")
        if isinstance(node_id, str) and node_id.strip():
            return f"ucs://local/{node_id}#container"
        return f"ucs://anon/{datetime.utcnow().timestamp()}"

    def upsert_container_node(self, meta: Dict[str, Any]) -> str:
        nid = self._node_id(meta)
        stored = self.nodes.get(nid, {})
        stored_meta = {**stored, **meta}
        stored_meta.setdefault("kind", "container")
        self.nodes[nid] = stored_meta
        return nid

    def link(self, src: str, dst: str, rel: str, meta: Dict[str, Any] | None = None) -> None:
        edge = (src, rel, dst)
        if edge in self.edges:
            return
        self.edges.add(edge)
        self.out[src].add((rel, dst))
        self.in_[dst].add((rel, src))

    def inject_glyph(
        self,
        content: Any,
        glyph_type: str,
        metadata: Dict[str, Any],
        region: str,
        plugin: str,
        container_id: str,
    ) -> str:
        """
        Generic glyph injection into stub KG.
        Mirrors KnowledgeGraphWriter.inject_glyph (simplified).
        """
        node_id = f"ucs://glyph/{datetime.utcnow().timestamp()}"
        self.nodes[node_id] = {
            "id": node_id,
            "content": content,
            "glyph_type": glyph_type,
            "metadata": metadata,
            "region": region,
            "plugin": plugin,
            "container_id": container_id,
        }
        if container_id:
            self.link(container_id, node_id, "contains")
        return node_id

    def write_scroll(self, scroll: Dict[str, Any]) -> str:
        """
        Store a reflection/relevance scroll in the KG as a glyph.
        API-compatible with KnowledgeGraphWriter usage.
        """
        container_id = scroll.get("container_id", "ucs://local/default#container")
        content = scroll.get("content", {})
        metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "tags": scroll.get("tags", []),
            "observer": scroll.get("observer"),
            **scroll.get("metadata", {}),
        }
        return self.inject_glyph(
            content=content,
            glyph_type="scroll",
            metadata=metadata,
            region="reflection_bridge",
            plugin="KGWriterStub",
            container_id=container_id,
        )


# ──────────────────────────────
# Global Stub Instance (mirrors real KG writer export)
# ──────────────────────────────
kg_writer = KGWriterStub()

__all__ = ["KGWriterStub", "kg_writer"]