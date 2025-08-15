# -*- coding: utf-8 -*-
# backend/modules/physics/physics_kernel_ingest.py
from __future__ import annotations
from typing import Dict, Any
from datetime import datetime

from backend.modules.sqi.sqi_container_registry import sqi_registry
from backend.modules.sqi.sqi_materializer import materialize_entry
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter

def ingest_physics_fact(name: str, data: Dict[str, Any], container_id: str | None = None) -> Dict[str, Any]:
    """
    Minimal ingest stub: routes (or honors explicit container_id) and writes a KG node.
    Address pattern: ucs://knowledge/facts/physics.kernel/<name>
    """
    # Resolve target container
    cid = (container_id or data.get("container_id"))
    if not cid:
        entry = sqi_registry.choose_for(domain="physics.kernel", kind="fact")
        cid = entry["id"] if isinstance(entry, dict) else entry

    # Ensure the container is materialized on disk (so inject_node can save)
    entry = sqi_registry.get(cid)
    if entry:
        try:
            # materialize_entry is idempotent (will just return existing)
            materialize_entry(entry)
        except Exception:
            pass

    # Build node & persist
    kg = KnowledgeGraphWriter()
    node_id = data.get("id", name)
    node = {
        "id": node_id,
        "label": data.get("label", name),
        "domain": data.get("domain", "physics.kernel"),
        "tags": data.get("tags", []),
        "ingested_at": datetime.utcnow().isoformat(),
    }
    out = kg.inject_node(container_id=cid, node=node)

    return {"status": "ok", "container_id": cid, "node_id": node_id, "path": out.get("path")}