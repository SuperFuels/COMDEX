# backend/modules/holo/hst_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .hst_ir import HoloSemanticTree, HSTNode, HSTEdge
from .holo_ir import HoloIR
from .holo_service import export_holo_from_kg_pack


def build_hst_from_source(
    *,
    source: str,
    language: str,
    container_id: str = "devtools:code",
    tick: int = 0,
    revision: int = 1,
) -> HoloSemanticTree:
    """
    SUPER MINIMAL HST BUILDER (safe default).

    We don't depend on CodexAST here yet, to avoid tight coupling.
    Instead we:
      - create one root "program" node
      - stash source + language in metadata
    You can later replace this with a real CodexAST → HST transform.
    """
    hst_id = f"hst:container/{container_id}/t={tick}/v{revision}"

    root = HSTNode(
      id="hst:root",
      kind="program",
      label="program",
      language=language,
      props={
          "line_count": len(source.splitlines()),
          "preview": source[:256],
      },
    )

    tree = HoloSemanticTree(
        id=hst_id,
        container_id=container_id,
        language=language,
        nodes=[root],
        edges=[],
        metadata={
            "tick": tick,
            "revision": revision,
            "source_language": language,
            "source_summary": {
                "line_count": len(source.splitlines()),
            },
        },
    )

    return tree


def hst_to_kg_pack(hst: HoloSemanticTree) -> Dict[str, Any]:
    """
    Convert an HST into a KG-like "pack" the Holo export code can understand.
    This is intentionally generic: nodes + links + metadata.
    """
    nodes = []
    links = []

    for n in hst.nodes:
        nodes.append(
            {
                "id": n.id,
                "type": n.kind,
                "label": n.label or n.id,
                "language": n.language or hst.language,
                "data": {
                    **(n.props or {}),
                    "kind": n.kind,
                    "language": n.language or hst.language,
                },
            }
        )

    for i, e in enumerate(hst.edges):
        links.append(
            {
                "id": e.id or f"hst-link-{i}",
                "src": e.src,
                "dst": e.dst,
                "kind": e.kind,
                "data": {"kind": e.kind},
            }
        )

    pack: Dict[str, Any] = {
        "container_id": hst.container_id,
        "nodes": nodes,
        "links": links,
        "meta": {
            "source": "hst_from_code",
            "language": hst.language,
            "hst_id": hst.id,
        },
    }
    return pack


def build_holo_from_hst(
    hst: HoloSemanticTree,
    *,
    tick: int = 0,
    frame: str = "original",
    revision: int = 1,
) -> HoloIR:
    """
    Bridge HST → KG pack → HoloIR.

    Uses export_holo_from_kg_pack so it goes through the same persistence
    + indexing path as normal container exports.
    """
    view_ctx: Dict[str, Any] = {
        "tick": tick,
        "frame": frame,
        "reason": "hst_from_code",
        "source_view": "code",
        "t_label": f"t={tick}",
        "views": {
            "code_view": {
                "language": hst.language,
            }
        },
        "metrics": {
            "tick": tick,
            # you can plug real metrics later
            "coherence": 1.0,
            "drift": 0.0,
        },
        "tags": ["hst", "code", hst.language],
    }

    kg_pack = hst_to_kg_pack(hst)
    holo = export_holo_from_kg_pack(
        container_id=hst.container_id,
        kg_pack=kg_pack,
        view_ctx=view_ctx,
        revision=revision,
    )
    return holo