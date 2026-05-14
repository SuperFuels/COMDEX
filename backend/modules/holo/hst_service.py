# backend/modules/holo/hst_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import re

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

# Optional KG writer – we degrade gracefully if it is missing
try:
    from backend.modules.knowledge_graph.knowledge_graph_writer import (
        kg_writer as _kg_writer,
    )
except Exception:
    _kg_writer = None

# Holo export helper: KG pack → .holo
from backend.modules.holo.holo_service import export_holo_from_kg_pack

# Optional QWave export – only used if present
try:
    from backend.modules.glyphwave.qwave.qwave_writer import (
        export_qwave_beams as _export_qwave_beams,
    )
except Exception:
    _export_qwave_beams = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -------------------------------------------------------------------
# Helpers for richer HST from source
# -------------------------------------------------------------------


_BLOCK_PATTERNS: List[tuple[re.Pattern, str]] = [
    # Python-style
    (re.compile(r"^\s*async\s+def\s+([A-Za-z_][A-Za-z0-9_]*)"), "function"),
    (re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)"), "function"),
    (re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)"), "class"),
    # JS/TS-style
    (re.compile(r"^\s*(?:export\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)"), "function"),
    (
        re.compile(
            r"^\s*(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(.*\)\s*=>"
        ),
        "function",
    ),
]


def _detect_block(line: str) -> Optional[Dict[str, str]]:
    """
    Heuristic: detect a “block head” (function/class/top-level op).
    Returns {name, kind} or None.
    """
    for pattern, kind in _BLOCK_PATTERNS:
        m = pattern.match(line)
        if m:
            return {"name": m.group(1), "kind": kind}
    return None


def _split_source_into_blocks(source: str) -> List[Dict[str, Any]]:
    """
    Very lightweight “parser”:
      • splits source into blocks by function/class-like headers
      • if nothing is found, returns a single block for the whole file
    """
    lines = source.splitlines()
    blocks: List[Dict[str, Any]] = []

    current: Dict[str, Any] = {
        "name": "program_root",
        "kind": "program",
        "start": 0,
        "lines": [],
    }

    for idx, line in enumerate(lines):
        hdr = _detect_block(line)
        if hdr:
            # close current block
            if current["lines"]:
                current["end"] = idx
                blocks.append(current)
            current = {
                "name": hdr["name"],
                "kind": hdr["kind"],
                "start": idx,
                "lines": [line],
            }
        else:
            current["lines"].append(line)

    # close final block
    if current["lines"]:
        current.setdefault("end", len(lines))
        blocks.append(current)

    # Fallback: whole file as one program block
    if not blocks:
        blocks.append(
            {
                "name": "program_root",
                "kind": "program",
                "start": 0,
                "end": len(lines),
                "lines": lines,
            }
        )

    return blocks


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
    Richer HST builder for U3A:

      code/AST → HST → KG pack → .holo

    Now:
      • one HST node per detected block (function/class/“program root”)
      • simple flow edges between consecutive blocks
      • lightweight metadata for QFC overlays (order, span, snippet)
    """
    blocks = _split_source_into_blocks(source)

    hst_nodes: List[Dict[str, Any]] = []
    for idx, b in enumerate(blocks):
        start = int(b.get("start", 0))
        end = int(b.get("end", start))
        block_src = "\n".join(b.get("lines", []))

        node_id = f"{b['kind']}_{b['name']}"
        hst_nodes.append(
            {
                "id": node_id,
                "kind": b.get("kind", "block"),
                "label": b.get("name", node_id),
                "language": language,
                "order": idx,
                "span": {
                    "start_line": start,
                    "end_line": end,
                },
                "source_excerpt": block_src[:1024],
            }
        )

    # simple linear control-flow edges between consecutive blocks
    hst_edges: List[Dict[str, Any]] = []
    for i in range(len(hst_nodes) - 1):
        src_id = hst_nodes[i]["id"]
        dst_id = hst_nodes[i + 1]["id"]
        hst_edges.append(
            {
                "src": src_id,
                "dst": dst_id,
                "kind": "flow",
            }
        )

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
        "nodes": hst_nodes,
        "edges": hst_edges,
    }
    return hst


def _build_hst_from_holo(holo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Richer HST: represent program frames + GHX edges instead of a single program_root.
    """
    extra = holo.get("extra") or {}
    program_frames: List[Dict[str, Any]] = extra.get("program_frames") or []

    ghx = holo.get("ghx") or {}
    edges = ghx.get("edges") or ghx.get("links") or []

    # HST nodes: 1 per program_frame (or a single root if none)
    hst_nodes: List[Dict[str, Any]] = []

    for idx, f in enumerate(program_frames):
        fid = f.get("id") or f"frame_{idx}"
        hst_nodes.append(
            {
                "id": fid,
                "kind": f.get("role", "frame"),
                "label": f.get("label", fid),
                "order": idx,
            }
        )

    if not hst_nodes:
        # Fallback: single program_root node
        cid = holo.get("container_id") or "unknown"
        hst_nodes.append(
            {
                "id": "program_root",
                "kind": "root",
                "label": holo.get("name") or cid,
                "order": 0,
            }
        )

    # HST edges: map GHX edges between frames (or generic flow edges)
    hst_edges: List[Dict[str, Any]] = []
    for e in edges:
        if not isinstance(e, dict):
            continue
        src = (
            e.get("source")
            or e.get("src")
            or e.get("from")
            or e.get("src_id")
        )
        dst = (
            e.get("target")
            or e.get("dst")
            or e.get("to")
            or e.get("dst_id")
        )
        if not src or not dst:
            continue
        hst_edges.append(
            {
                "src": src,
                "dst": dst,
                "kind": e.get("kind", "flow"),
            }
        )

    return {
        "nodes": hst_nodes,
        "edges": hst_edges,
        "meta": {
            "holo_id": holo.get("holo_id"),
            "container_id": holo.get("container_id"),
        },
    }


# -------------------------------------------------------------------
# HST → QWave beams
# -------------------------------------------------------------------


def hst_to_qwave_beams(hst: Dict[str, Any], mode: str = "qqc") -> List[Dict[str, Any]]:
    """
    Very simple HST → beam adapter:
      • one beam per HST edge

    These beams can later be fed into qwave_writer.export_qwave_beams(...)
    or embedded into KG/Holo packs for QFC overlays.
    """
    beams: List[Dict[str, Any]] = []
    for idx, e in enumerate(hst.get("edges") or []):
        if not isinstance(e, dict):
            continue
        src = e.get("src") or e.get("source")
        dst = e.get("dst") or e.get("target")
        if not src or not dst:
            continue
        beams.append(
            {
                "id": e.get("id") or f"hst-beam-{idx}",
                "source": src,
                "target": dst,
                "carrier_type": "HST_FLOW",
                "modulation": mode,
                "coherence": 1.0,
                "entangled_path": [src, dst],
                "collapse_state": "original",
                "mutation_trace": [],
                "metadata": {
                    "from_hst": True,
                    "kind": e.get("kind", "flow"),
                },
            }
        )
    return beams


# -------------------------------------------------------------------
# HST → KG pack (explicit step for U3A)
# -------------------------------------------------------------------


def build_kg_pack_from_hst(hst: Dict[str, Any]) -> Dict[str, Any]:
    """
    Turn an HST into a KG pack suitable for GHX / .holo.

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
    for idx, n in enumerate(h_nodes):
        kg_nodes.append(
            {
                "id": n.get("id"),
                "label": n.get("label") or n.get("kind") or "node",
                "type": n.get("kind") or "hst_node",
                "order": n.get("order", idx),
                "layout": {"row": 0, "col": idx},
                "data": n,
            }
        )

    kg_links: List[Dict[str, Any]] = []
    for e in h_edges:
        src = e.get("src") or e.get("source")
        dst = e.get("dst") or e.get("target")
        if not src or not dst:
            continue
        kg_links.append(
            {
                "id": e.get("id"),
                "source": src,
                "target": dst,
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
    It also:
      • derives simple HST-based beams and attaches them to the pack meta.
    """
    meta = hst.get("meta", {}) or {}
    container_id = meta.get("container_id") or "devtools:code"

    # 1) Explicit KG pack step (U3A requirement)
    kg_pack = build_kg_pack_from_hst(hst)

    # 2) Derive simple beams from HST edges (HST → QWave bridge)
    hst_beams = hst_to_qwave_beams(hst, mode="qqc")
    if hst_beams:
        # Keep it simple: stash beams in pack meta so DevTools/QFC can read them.
        kg_pack.setdefault("meta", {})
        kg_pack["meta"]["hst_beams"] = hst_beams
        kg_pack["meta"]["has_hst_beams"] = True

        # Optional: if real qwave exporter exists, pre-materialise a beam pack
        if _export_qwave_beams is not None:
            try:
                container_stub: Dict[str, Any] = {
                    "id": container_id,
                    "glyph_grid": [],
                    "symbolic": {},
                }
                _export_qwave_beams(
                    container_stub,
                    hst_beams,
                    context={"frame": frame, "source": "hst_from_code"},
                )
                # expose whatever structure qwave_writer produced
                if "qwave_beams" in container_stub:
                    kg_pack["meta"]["qwave_beams"] = container_stub["qwave_beams"]
                elif "symbolic" in container_stub and isinstance(
                    container_stub["symbolic"], dict
                ):
                    qsym = container_stub["symbolic"].get("qwave_beams")
                    if qsym:
                        kg_pack["meta"]["qwave_beams"] = qsym
            except Exception as e:
                print(f"[HST] export_qwave_beams from HST failed: {e}")

    # 3) View context – carried into the HoloIR field/indexing
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
        # expose beams for UI/QFC if needed
        "qwave_from_hst": {
            "beams": hst_beams,
            "mode": "qqc",
        },
    }

    # 4) Holo export (writes .holo JSON under HOLO_ROOT/<cid>/...)
    holo = export_holo_from_kg_pack(
        container_id=container_id,
        kg_pack=kg_pack,
        view_ctx=view_ctx,
        revision=revision,
    )
    return holo


# -------------------------------------------------------------------
# U3C – Rehydrate from .holo → HST + KG
# -------------------------------------------------------------------


def rehydrate_hst_from_holo(holo: Dict[str, Any]) -> Dict[str, Any]:
    """
    .holo → HST → KG:
      • builds a richer HST from program_frames + GHX edges
      • injects nodes/links into the KnowledgeGraphWriter
      • lets QFC reuse the KG pack / layout
    """
    hst = _build_hst_from_holo(holo)

    container_id = (
        holo.get("container_id")
        or (hst["meta"].get("container_id") if "meta" in hst else None)
        or "holo::rehydrated"
    )

    writer = get_kg_writer()

    # Map HST into a simple domain pack {id, nodes, links}
    pack: Dict[str, Any] = {
        "id": container_id,
        "name": holo.get("name") or container_id,
        "metadata": {
            "domain": "holo_rehydrated",
            "source": "rehydrate_hst_from_holo",
            "holo_id": holo.get("holo_id"),
        },
        "nodes": [],
        "links": [],
    }

    for n in hst.get("nodes", []):
        if not isinstance(n, dict):
            continue
        nid = n.get("id")
        if not nid:
            continue
        pack["nodes"].append(
            {
                "id": nid,
                "label": n.get("label", nid),
                "cat": n.get("kind", "frame"),
            }
        )

    for e in hst.get("edges", []):
        if not isinstance(e, dict):
            continue
        src = e.get("src")
        dst = e.get("dst")
        if not src or not dst:
            continue
        pack["links"].append(
            {
                "src": src,
                "dst": dst,
                "relation": e.get("kind", "flow"),
            }
        )

    # Ingest into live KG (nodes + edges, plus auto-export)
    kg_loaded = writer.load_domain_pack(container_id, pack)

    return {
        "hst": hst,
        "kg": {
            "loaded": bool(kg_loaded),
            "container_id": container_id,
            "node_count": len(pack["nodes"]),
            "edge_count": len(pack["links"]),
        },
    }