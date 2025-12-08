# backend/modules/holo/hst_service.py
from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime, timezone

# Optional KG writer – we degrade gracefully if it is missing
try:
    from backend.modules.knowledge_graph.knowledge_graph_writer import (
        kg_writer as _kg_writer,
    )
except Exception:
    _kg_writer = None

# Holo export helper: KG pack → .holo
from backend.modules.holo.holo_service import export_holo_from_kg_pack


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -------------------------------------------------------------------
# HST construction (code → HST)
# -------------------------------------------------------------------


def build_hst_from_source(
    *,
    source: str,
    language: str,
    container_id: str,
    tick: int = 0,
    revision: int = 1,
) -> Dict[str, Any]:
    """
    Very minimal HST builder used for U3A:

      code/AST → HST → KG pack → .holo

    Right now this is intentionally simple: a single 'program' node with the
    source snippet attached. You can replace this with a real CodexAST → HST
    transform later.
    """
    hst: Dict[str, Any] = {
        "meta": {
            "container_id": container_id,
            "language": language,
            "tick": tick,
            "revision": revision,
            "created_at": _utc_now_iso(),
            "name": f"{language} program",
            "symbol": "PROGRAM",
        },
        "nodes": [
            {
                "id": "program_root",
                "kind": "program",
                "language": language,
                "label": "Program",
                "source_excerpt": source[:1024],
            }
        ],
        "edges": [],  # no internal structure yet
    }
    return hst


# -------------------------------------------------------------------
# HST → KG pack (explicit step for U3A)
# -------------------------------------------------------------------


def build_kg_pack_from_hst(hst: Dict[str, Any]) -> Dict[str, Any]:
    """
    Turn a minimal HST into a KG pack suitable for GHX / .holo.

    If the global kg_writer exposes a richer HST path
      (e.g. kg_writer.build_pack_from_hst(hst)),
    we call that. Otherwise we fall back to a simple "nodes+links" pack.
    """
    # 1) Prefer a dedicated kg_writer hook if present
    if _kg_writer is not None and hasattr(_kg_writer, "build_pack_from_hst"):
        try:
            return _kg_writer.build_pack_from_hst(hst)  # type: ignore[attr-defined]
        except Exception as e:
            print(f"[HST] kg_writer.build_pack_from_hst failed: {e}")

    # 2) Fallback: simple, generic KG pack from HST structure
    meta = hst.get("meta", {}) or {}
    h_nodes: List[Dict[str, Any]] = (hst.get("nodes") or [])[:]
    h_edges: List[Dict[str, Any]] = (hst.get("edges") or [])[:]

    kg_nodes: List[Dict[str, Any]] = []
    for n in h_nodes:
        kg_nodes.append(
            {
                "id": n.get("id"),
                "label": n.get("label") or n.get("kind") or "node",
                "type": n.get("kind") or "hst_node",
                "data": n,
            }
        )

    kg_links: List[Dict[str, Any]] = []
    for e in h_edges:
        kg_links.append(
            {
                "id": e.get("id"),
                "source": e.get("source"),
                "target": e.get("target"),
                "type": e.get("kind") or "hst_edge",
                "data": e,
            }
        )

    pack: Dict[str, Any] = {
        "nodes": kg_nodes,
        "links": kg_links,
        "meta": {
            "name": meta.get("name"),
            "symbol": meta.get("symbol"),
            "language": meta.get("language"),
            "layout": "hst_program",
            "entangled_links": [],
        },
    }
    return pack


# -------------------------------------------------------------------
# HST → KG pack → .holo (export)
# -------------------------------------------------------------------


def build_holo_from_hst(
    hst: Dict[str, Any],
    *,
    tick: int = 0,
    frame: str = "original",
    revision: int = 1,
):
    """
    Full U3A path:

      code/AST → HST → KG pack → .holo

    This function performs the explicit KG pack step and then calls
    export_holo_from_kg_pack(...) which writes the .holo JSON to disk.
    """
    meta = hst.get("meta", {}) or {}
    container_id = meta.get("container_id") or "devtools:code"

    # 1) Explicit KG pack step (U3A requirement)
    kg_pack = build_kg_pack_from_hst(hst)

    # 2) View context – carried into the HoloIR field/indexing
    view_ctx: Dict[str, Any] = {
        "tick": tick,
        "frame": frame,
        "t_label": f"tick_{tick}",
        "kind": "memory",
        "psi_state": {
            "source": "hst_from_code",
        },
        "views": {
            "hst": hst,
        },
        "tags": ["hst_from_code"],
        "metrics": {
            "tick": tick,
        },
    }

    # 3) Holo export (writes .holo JSON under HOLO_ROOT/<cid>/...)
    holo = export_holo_from_kg_pack(
        container_id=container_id,
        kg_pack=kg_pack,
        view_ctx=view_ctx,
        revision=revision,
    )
    return holo


# -------------------------------------------------------------------
# U3C – Rehydrate from .holo → HST-like dict
# -------------------------------------------------------------------


def rehydrate_hst_from_holo(holo: Dict[str, Any]) -> Dict[str, Any]:
    """
    VERY minimal U3C skeleton:

      .holo → HST-like dict

    Later you can swap this for a real HST model + kg_writer integration.
    """
    ghx = holo.get("ghx") or {}
    nodes = ghx.get("nodes") or []
    edges = ghx.get("edges") or ghx.get("links") or []

    timefold = holo.get("timefold") or {}

    return {
        "kind": "rehydrated_hst",
        "container_id": holo.get("container_id"),
        "holo_id": holo.get("holo_id"),
        "tick": timefold.get("tick"),
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "extra": holo.get("extra") or {},
        },
    }