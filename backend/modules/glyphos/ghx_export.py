# -*- coding: utf-8 -*-
# backend/modules/glyphos/ghx_export.py
from __future__ import annotations
from datetime import datetime
from typing import Dict, Any, List

def _collect_nodes_from_grid(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes = []
    for g in (container.get("glyph_grid") or []):
        if isinstance(g, dict) and g.get("type") == "kg_node":
            md = g.get("metadata", {})
            if isinstance(md, dict) and md.get("id"):
                nodes.append({
                    "id": md.get("id"),
                    "label": md.get("label"),
                    "domain": md.get("domain"),
                    "tags": md.get("tags", []),
                    "type": "kg_node",
                })
    return nodes

def _collect_nodes_legacy(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for n in (container.get("nodes") or []):
        if isinstance(n, dict) and n.get("id"):
            out.append({"type": "kg_node", **n})
    return out

def encode_glyphs_to_ghx(
    container: Dict[str, Any],
    *,
    qglyph_string: str = "",
    observer_id: str = "anon",
) -> Dict[str, Any]:
    """
    HOV3-aware GHX encoder:
      - Honors meta.ghx.collapsed/density and meta.time_dilation if present
      - Merges nodes from both `container["nodes"]` (legacy) and `glyph_grid` (type="kg_node")
      - Emits counts that match serialized arrays
    """
    c = dict(container or {})
    meta = (c.get("meta") or {}) if isinstance(c.get("meta"), dict) else {}
    ghx_flags = meta.get("ghx") or {}
    glyphs = list(c.get("glyphs") or [])

    # Merge node sources (glyph_grid wins on collisions)
    merged: Dict[str, Dict[str, Any]] = {}
    for n in _collect_nodes_legacy(c):
        nid = n.get("id")
        if nid:
            merged[nid] = n
    for n in _collect_nodes_from_grid(c):
        nid = n.get("id")
        if nid:
            merged[nid] = n  # prefer grid version

    nodes = list(merged.values())

    payload = {
        "version": "1.0",
        "rendered_at": datetime.utcnow().isoformat(),
        "container_id": c.get("id"),
        "observer_id": observer_id or "anon",
        "flags": {
            "collapsed": bool(ghx_flags.get("collapsed", True)),
            "density": ghx_flags.get("density", "auto"),
            "time_dilation": meta.get("time_dilation") or {"mode": "normal", "snapshot_rate": 1.0},
        },
        "counts": {
            "glyphs": len(glyphs),
            "nodes": len(nodes),
        },
        "glyphs": glyphs,
        "nodes": nodes,
        "qglyph_echo": qglyph_string or None,
        "meta": {
            "address": meta.get("address"),
            "ghx": {
                "hover": bool(ghx_flags.get("hover", True)),
                "collapsed": bool(ghx_flags.get("collapsed", True)),
                "density": ghx_flags.get("density", "auto"),
                "version": ghx_flags.get("version", "1.0"),
            },
            "hov": meta.get("hov"),
            "last_updated": meta.get("last_updated"),
        },
    }
    return payload