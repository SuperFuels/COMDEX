# backend/modules/sqi/sqi_metadata_embedder.py
from __future__ import annotations
from typing import Dict, Any
from datetime import datetime

# --- HOV4: Time-dilation thresholds (tune as you like) ---
_TIME_DILATION = {
    "glyphs_compress_at": 1000,   # over this -> compressed
    "glyphs_freeze_at":   5000,   # over this -> frozen
    "nodes_compress_at":  1000,
    "nodes_freeze_at":    5000,
    "compressed_rate":    0.1,    # keep ~10% when compressing
}

def _compute_time_dilation(stats: dict | None) -> dict:
    s = stats or {}
    glyphs = int((s.get("glyphs") or 0))
    nodes  = int((s.get("nodes")  or 0))

    # pick stronger mode from glyphs/nodes
    glyph_mode = "normal"
    if glyphs >= _TIME_DILATION["glyphs_freeze_at"]:
        glyph_mode = "frozen"
    elif glyphs >= _TIME_DILATION["glyphs_compress_at"]:
        glyph_mode = "compressed"

    node_mode = "normal"
    if nodes >= _TIME_DILATION["nodes_freeze_at"]:
        node_mode = "frozen"
    elif nodes >= _TIME_DILATION["nodes_compress_at"]:
        node_mode = "compressed"

    mode = "normal"
    for m in ("frozen", "compressed"):
        if glyph_mode == m or node_mode == m:
            mode = m
            break

    return {
        "mode": mode,  # normal | compressed | frozen
        "snapshot_rate": _TIME_DILATION["compressed_rate"] if mode == "compressed" else (0.0 if mode == "frozen" else 1.0),
        "reason": {
            "glyphs": glyphs,
            "nodes": nodes
        }
    }

HOV_DEFAULTS = {
    "hover": True,
    "collapsed": True,   # default to collapsed -> lightweight by default
    "density": "auto",
    "version": "1.0",
}

def _merge(a: dict | None, b: dict) -> dict:
    out = dict(a or {})
    for k, v in b.items():
        if isinstance(v, dict):
            out[k] = _merge(out.get(k) if isinstance(out.get(k), dict) else {}, v)
        else:
            out[k] = v
    return out

def bake_hologram_meta(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure a container carries GHX (hover/collapse) metadata + minimal HOV hints.
    HOV1 + HOV2 + HOV4
    """
    meta = dict(container.get("meta") or {})

    # Merge defaults for GHX hover/collapse
    meta["ghx"] = _merge(meta.get("ghx"), HOV_DEFAULTS)

    # Hint for lazy loading
    meta.setdefault("hov", {"lazy_ready": True})

    # --- HOV4: compute and stamp time-dilation state based on size ---
    stats = meta.get("stats") or {}
    meta["time_dilation"] = _compute_time_dilation(stats)

    # Update embed timestamp
    meta["last_hov_embed"] = datetime.utcnow().isoformat()

    container["meta"] = meta

    # Keep container lightweight by default
    container.setdefault("nodes", [])
    container.setdefault("glyphs", [])

    return container

def make_kg_payload(entry: Dict[str, Any], *, expand: bool = False) -> Dict[str, Any]:
    """
    Produce a KG node payload reflecting HOV flags.
    HOV2 + HOV3: if collapsed and expand=False -> headers only
    """
    cid = entry["id"]
    meta = dict(entry.get("meta") or {})
    ghx = meta.get("ghx") or {}
    collapsed = ghx.get("collapsed", True)

    node = {
        "id": cid,
        "kind": "container",
        "meta": meta,
        "viz": {
            "ghx_hover": bool(ghx.get("hover", True)),
            "ghx_collapsed": bool(collapsed),
        },
    }

    if expand or not collapsed:
        # expanded view can include heavier hints (but not full blobs here)
        node["expansion"] = {
            "includes": ["nodes_stub", "glyphs_stub"],
            "counts": {
                "nodes": int(meta.get("stats", {}).get("nodes", 0)),
                "glyphs": int(meta.get("stats", {}).get("glyphs", 0)),
            }
        }
    else:
        node["expansion"] = {"includes": [], "counts": {}}

    return node