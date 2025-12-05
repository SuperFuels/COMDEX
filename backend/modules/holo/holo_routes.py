# backend/modules/holo/holo_routes.py
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from backend.modules.holo.holo_service import (
    export_holo_from_container,
    load_latest_holo_for_container,
    load_holo_history_for_container,
    load_holo_index_for_container,
    load_holo_for_container_at,
    search_holo_index,
)
from backend.modules.runtime.container_runtime import get_container_runtime

router = APIRouter(
    prefix="/holo",
    tags=["holo"],
)


@router.post("/export/{container_id}")
def export_holo(
    container_id: str,
    view_ctx: Dict[str, Any] = Body(default={}),
    revision: int = 1,
):
    """
    Export a fresh HoloIR snapshot for a container and persist it as .holo.json.

    Internally:
      - ContainerRuntime.load_and_activate_container(container_id)
      - export_holo_from_container(container, view_ctx, revision)
      - Writes to HOLO_ROOT/<cid>/...t=<tick>_v<rev>.holo.json (plus optional index entry)
    """
    cr = get_container_runtime()
    # load/activate container (handles data/containers vs modules path)
    container = cr.load_and_activate_container(container_id)

    holo = export_holo_from_container(container, view_ctx, revision=revision)
    return getattr(holo, "__dict__", holo)


@router.get("/container/{container_id}/latest")
def get_latest_holo(container_id: str):
    """
    Return the most recent .holo snapshot for this container, if any.
    """
    holo = load_latest_holo_for_container(container_id)
    if not holo:
        # 404 is fine – frontend treats 'no holo yet' as non-fatal
        raise HTTPException(status_code=404, detail="no_holo_for_container")

    return getattr(holo, "__dict__", holo)


@router.get("/container/{container_id}/history")
def get_holo_history(container_id: str):
    """
    Lightweight history view for a container's holos.
    Backed by holo_index.json so it survives restarts.
    """
    entries = load_holo_history_for_container(container_id)
    # OK to return [] if nothing yet
    return entries


@router.get("/container/{container_id}/index")
def get_holo_index(container_id: str):
    """
    Return a lightweight index of all holo snapshots for this container.

    Shape:
      [
        {
          "holo_id": "...",
          "container_id": "...",
          "tick": 0,
          "revision": 1,
          "created_at": "...",
          "tags": [...],
          "path": "...",     # server-side path (for debugging)
          "mtime": 123456.0, # file mtime (epoch seconds)
        },
        ...
      ]
    """
    entries = load_holo_index_for_container(container_id)
    # Even if empty, 200 + [] is valid (no snapshots yet)
    return entries


@router.get("/container/{container_id}/at")
def get_holo_at(container_id: str, tick: int, revision: int = 1):
    """
    Load a specific holo snapshot by (container_id, tick, revision).
    """
    holo = load_holo_for_container_at(container_id, tick, revision)
    if not holo:
        raise HTTPException(
            status_code=404,
            detail=f"no_holo_for_container_at_tick:{container_id}:t={tick}:v={revision}",
        )

    return getattr(holo, "__dict__", holo)


@router.get("/index/search")
def search_holo_index_route(
    container_id: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
):
    """
    Global search over holo_index.json.

    Filters:
      - container_id (optional)
      - tag (optional, must be in entry.tags)

    Returns newest → oldest.
    """
    return search_holo_index(container_id=container_id, tag=tag)