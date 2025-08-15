# -*- coding: utf-8 -*-
# backend/routes/ghx_encode.py
from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Body

# UCS container access
from backend.modules.dimensions.universal_container_system import ucs_runtime

# Try the real encoder if you have it; otherwise we’ll fall back safely.
try:
    from backend.modules.glyphos.ghx_export import encode_glyphs_to_ghx as _real_ghx_encoder  # type: ignore
except Exception:
    _real_ghx_encoder = None  # fallback below


router = APIRouter(prefix="/sqi/ghx", tags=["GHX"])


# -------------------------
# Utilities
# -------------------------
def _get_container(cid: str) -> dict:
    """
    Best-effort lookup for a UCS container by id.
    """
    try:
        if hasattr(ucs_runtime, "get_container"):
            c = ucs_runtime.get_container(cid)
        elif hasattr(ucs_runtime, "index"):
            c = ucs_runtime.index.get(cid)
        elif hasattr(ucs_runtime, "registry"):
            c = ucs_runtime.registry.get(cid)
        else:
            c = None
    except Exception:
        c = None
    if not c:
        raise HTTPException(status_code=404, detail=f"Unknown container: {cid}")
    return c


def _sample(items: List[Any], step: int) -> List[Any]:
    if step <= 1:
        return list(items)
    return [it for i, it in enumerate(items) if i % step == 0]


def _clean_glyph(g: Any) -> Dict[str, Any]:
    """
    Remove heavy/irrelevant fields but keep stable metadata for GHX preview.
    Supports both glyph dicts and simple strings.
    """
    if not isinstance(g, dict):
        return {"text": str(g), "type": "glyph"}
    keep = {
        "id": g.get("id"),
        "type": g.get("type") or "glyph",
        "content": g.get("content") or g.get("glyph"),
        "metadata": g.get("metadata") or g.get("meta") or {},
        "agent_id": g.get("agent_id") or g.get("agent"),
        "timestamp": g.get("timestamp"),
        "tags": g.get("tags") or [],
    }
    return keep


def _density_to_step(density: str | None) -> int:
    """
    Convert GHX density policy to a sampling step. Lower step = more detail.
    """
    d = (density or "").lower()
    if d in ("max", "full", "high"):
        return 1
    if d in ("med", "medium", "auto", ""):
        return 2
    if d in ("low", "min", "tiny"):
        return 4
    return 2


def _encode_ghx_fallback(
    container: Dict[str, Any],
    *,
    qglyph_string: str = "",
    observer_id: str = "anon",
    collapsed_override: Optional[bool] = None,
    density_override: Optional[str] = None,
    snapshot_rate_override: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Minimal HOV3-aware encoder used when the real encoder is not present.
    - Respects meta.ghx.collapsed, meta.ghx.density, meta.time_dilation.snapshot_rate
    - Returns a stable GHX packet that your frontend can consume immediately
    """
    meta: Dict[str, Any] = container.get("meta", {}) or {}
    ghx_meta: Dict[str, Any] = meta.get("ghx", {}) or {}
    td_meta: Dict[str, Any] = meta.get("time_dilation", {}) or {}

    collapsed = ghx_meta.get("collapsed", True) if collapsed_override is None else bool(collapsed_override)
    density = (density_override or ghx_meta.get("density") or "auto")
    snapshot_rate = float(td_meta.get("snapshot_rate", 1.0) if snapshot_rate_override is None else snapshot_rate_override)

    step = _density_to_step(density)

    # Pull content from common shapes
    glyphs_src = (
        container.get("glyphs")
        or container.get("glyph_grid")
        or []
    )
    nodes_src = container.get("nodes") or []

    glyphs: List[Dict[str, Any]] = []
    nodes: List[Dict[str, Any]] = []

    if not collapsed:
        glyphs = [_clean_glyph(g) for g in _sample(glyphs_src, step)]
        # nodes are typically lighter; still sample by density for consistency
        nodes = [n if isinstance(n, dict) else {"id": str(n)} for n in _sample(nodes_src, step)]

    return {
        "version": "1.0",
        "rendered_at": datetime.utcnow().isoformat(),
        "container_id": container.get("id") or container.get("container_id") or "unknown",
        "observer_id": observer_id,
        "flags": {
            "collapsed": bool(collapsed),
            "density": density,
            "time_dilation": {
                "mode": td_meta.get("mode", "normal"),
                "snapshot_rate": snapshot_rate,
            },
        },
        "counts": {
            "glyphs": len(glyphs_src),
            "nodes": len(nodes_src),
        },
        # Only include heavy arrays when not collapsed
        "glyphs": glyphs if not collapsed else [],
        "nodes": nodes if not collapsed else [],
        # Optional echo of a qglyph preview (for frontend overlays)
        "qglyph_echo": ({"text": qglyph_string, "len": len(qglyph_string)} if qglyph_string else None),
        # Handy meta passthrough for UI
        "meta": {
            "address": meta.get("address"),
            "ghx": ghx_meta,
            "hov": meta.get("hov"),
            "last_updated": meta.get("last_updated"),
        },
    }


def _encode_wrapper(
    container: Dict[str, Any],
    *,
    qglyph_string: str,
    observer_id: str,
    collapsed: Optional[bool],
    density: Optional[str],
    snapshot_rate: Optional[float],
) -> Dict[str, Any]:
    """
    Use the real encoder when available; otherwise fallback.
    Real encoder is expected to be HOV3-aware as well.
    """
    if _real_ghx_encoder:
        # Many repos standardize kwargs like these; pass only when provided.
        kwargs = {
            "qglyph_string": qglyph_string,
            "observer_id": observer_id,
        }
        if collapsed is not None:
            kwargs["collapsed"] = bool(collapsed)
        if density is not None:
            kwargs["density"] = density
        if snapshot_rate is not None:
            kwargs["snapshot_rate"] = float(snapshot_rate)
        return _real_ghx_encoder(container, **kwargs)  # type: ignore

    # Fallback path preserves HOV3 behavior
    return _encode_ghx_fallback(
        container,
        qglyph_string=qglyph_string,
        observer_id=observer_id,
        collapsed_override=collapsed,
        density_override=density,
        snapshot_rate_override=snapshot_rate,
    )


# -------------------------
# Routes
# -------------------------

@router.get("/encode/{cid}")
def ghx_encode_get(
    cid: str,
    qglyph_string: str = "",
    observer: Optional[str] = Query(default="anon"),
    collapsed: Optional[bool] = Query(default=None, description="Override meta.ghx.collapsed"),
    density: Optional[str] = Query(default=None, description="Override meta.ghx.density (low|auto|high)"),
    snapshot_rate: Optional[float] = Query(default=None, description="Override time_dilation.snapshot_rate"),
):
    """
    Returns a full GHX export for a container, respecting HOV3 flags.
    - collapsed=True  → light header (no heavy glyph/node arrays)
    - density + snapshot_rate honored where applicable
    """
    container = _get_container(cid)
    payload = _encode_wrapper(
        container,
        qglyph_string=qglyph_string,
        observer_id=observer or "anon",
        collapsed=collapsed,
        density=density,
        snapshot_rate=snapshot_rate,
    )
    return {"status": "ok", "cid": cid, "ghx": payload}


@router.post("/encode/{cid}")
def ghx_encode_post(
    cid: str,
    body: Dict[str, Any] = Body(default_factory=dict),
    observer: Optional[str] = Query(default="anon"),
    collapsed: Optional[bool] = Query(default=None),
    density: Optional[str] = Query(default=None),
    snapshot_rate: Optional[float] = Query(default=None),
):
    """
    POST variant for large qglyph payloads.
    Body may include: {"qglyph_string": "..."}.
    Query params can still override HOV3 flags.
    """
    qglyph_string = str(body.get("qglyph_string", "")) if isinstance(body, dict) else ""
    container = _get_container(cid)
    payload = _encode_wrapper(
        container,
        qglyph_string=qglyph_string,
        observer_id=observer or "anon",
        collapsed=collapsed,
        density=density,
        snapshot_rate=snapshot_rate,
    )
    return {"status": "ok", "cid": cid, "ghx": payload}