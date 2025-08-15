# backend/modules/sqi/sqi_materializer.py
from __future__ import annotations
from typing import Dict, Any

from backend.modules.dimensions.universal_container_system import ucs_runtime
from backend.modules.knowledge_graph.kg_writer_stub import KGWriterStub
from backend.modules.sqi.sqi_metadata_embedder import bake_hologram_meta  # HOV1/HOV2

kg_stub = KGWriterStub()

def materialize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Materialize an SQI registry entry into a UCS container, and mirror to KG.
      1) Bake holographic GHX metadata (hover/collapse) into the container (HOV1/HOV2)
      2) Register/merge in UCS (idempotent; address stamping handled by UCS)
      3) Upsert KG node (including GHX flags in meta)
      4) Link domain edge: container -[IN_DOMAIN]-> domain node

    Returns:
        Dict[str, Any]: The UCS container snapshot.
    """
    cid = entry["id"]
    meta = dict(entry.get("meta") or {})

    # Build minimal, UCS-friendly container skeleton (keeps prior structural fields)
    container = {
        "id": cid,
        "type": "container",
        "kind": entry.get("kind"),
        "domain": entry.get("domain"),
        "meta": meta,
        # structural fields we keep around for future population
        "atoms": {},
        "wormholes": [],
        "nodes": [],
        "glyphs": [],
    }

    # 1) HOV1/HOV2: bake hover/collapse GHX flags & lazy-ready hints
    container = bake_hologram_meta(container)

    # 2) UCS register/merge (idempotent)
    container = ucs_runtime.register_container(cid, container)

    # 3) KG node upsert with baked meta (includes ghx/hov flags & timestamps)
    node_id = kg_stub.upsert_container_node({
        "id": cid,
        "kind": "container",
        "meta": container.get("meta", {}),
    })

    # 4) KG domain link (create/ensure domain node, then link)
    domain = entry.get("domain") or "unknown"
    domain_id = f"domain://{domain}"
    kg_stub.upsert_container_node({
        "id": domain_id,
        "kind": "domain",
        "meta": {"label": domain},
    })
    kg_stub.link(node_id, domain_id, "IN_DOMAIN", meta={"via": "SQI"})

    return container