from __future__ import annotations
from typing import Dict, Any, Tuple, Set, DefaultDict
from collections import defaultdict
from datetime import datetime

class KGWriterStub:
    """
    Minimal in-memory KG writer.
    - upsert_container_node(meta) -> node_id (uses meta['address'] if present)
    - link(src, dst, rel, meta={})
    Intentionally tiny; swap later for your real KG writer.
    """
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}     # node_id -> meta
        self.edges: Set[Tuple[str, str, str]] = set()  # (src, rel, dst)
        self.out: DefaultDict[str, Set[Tuple[str, str]]] = defaultdict(set)
        self.in_: DefaultDict[str, Set[Tuple[str, str]]] = defaultdict(set)

    def _node_id(self, meta: Dict[str, Any]) -> str:
        # Prefer stable address if present, else fallback to id
        addr = (meta.get("meta") or {}).get("address") or meta.get("address")
        if isinstance(addr, str) and addr.strip():
            return addr
        node_id = meta.get("id")
        if isinstance(node_id, str) and node_id.strip():
            return f"ucs://local/{node_id}#container"
        # ultimate fallback: timestamp
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