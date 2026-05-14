# backend/modules/sqi/sqi_materializer.py
from __future__ import annotations

from typing import Any, Dict, Optional


# ──────────────────────────────────────────────
# Lazy deps (no UCS bring-up / no KG writer at import-time)
# ──────────────────────────────────────────────
_UCS_RUNTIME = None
_KG_STUB = None


def _get_ucs_runtime():
    global _UCS_RUNTIME
    if _UCS_RUNTIME is None:
        from backend.modules.dimensions.universal_container_system import ucs_runtime  # type: ignore
        _UCS_RUNTIME = ucs_runtime
    return _UCS_RUNTIME


def _get_kg_stub():
    global _KG_STUB
    if _KG_STUB is None:
        from backend.modules.knowledge_graph.kg_writer_stub import KGWriterStub  # type: ignore
        _KG_STUB = KGWriterStub()
    return _KG_STUB


def _bake_hologram_meta(container: Dict[str, Any]) -> Dict[str, Any]:
    # Prefer real embedder, but tolerate missing module in lean/GX1 environments.
    try:
        from backend.modules.sqi.sqi_metadata_embedder import bake_hologram_meta  # type: ignore
        return bake_hologram_meta(container)
    except Exception:
        # minimal no-op fallback
        meta = dict(container.get("meta") or {})
        ghx = dict((meta.get("ghx") or {}) if isinstance(meta.get("ghx"), dict) else {})
        ghx.setdefault("hover", True)
        ghx.setdefault("collapsed", True)
        meta["ghx"] = ghx
        container["meta"] = meta
        return container


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────
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
    if not isinstance(entry, dict):
        raise TypeError("materialize_entry expects a dict entry")

    cid = entry.get("id")
    if not cid:
        raise ValueError("materialize_entry entry missing 'id'")

    meta = dict(entry.get("meta") or {})

    # Build minimal, UCS-friendly container skeleton (keeps prior structural fields)
    container: Dict[str, Any] = {
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
    container = _bake_hologram_meta(container)

    # 2) UCS register/merge (idempotent)
    ucs_runtime = _get_ucs_runtime()
    container = ucs_runtime.register_container(cid, container)

    # 3) KG node upsert with baked meta (includes ghx/hov flags & timestamps)
    kg_stub = _get_kg_stub()
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


# ──────────────────────────────────────────────
# Back-compat: keep a name that older imports may reference
# (but avoid eager init)
# ──────────────────────────────────────────────
def get_kg_stub():
    return _get_kg_stub()
