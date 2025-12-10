# backend/modules/holo/holo_routes.py
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel

from backend.modules.holo.holo_service import save_holo_from_dict, list_holos_for_container

from backend.modules.holo.holo_service import (
    export_holo_from_container,
    load_latest_holo_for_container,
    load_holo_history_for_container,
    load_holo_index_for_container,
    load_holo_for_container_at,
    search_holo_index,
    save_holo_from_dict,
)
from backend.modules.holo.holo_execution_service import run_holo_snapshot
from backend.modules.holo.hst_service import (
    build_hst_from_source,
    build_holo_from_hst,
    rehydrate_hst_from_holo,
)
from backend.modules.runtime.container_runtime import get_container_runtime

router = APIRouter(
    prefix="/holo",  # app will usually mount this under /api → /api/holo/...
    tags=["holo"],
)

# -------------------------------------------------------------------
# Export: container → .holo
# -------------------------------------------------------------------


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


# -------------------------------------------------------------------
# Import: motif / external → .holo store
# -------------------------------------------------------------------


@router.post("/import")
def import_holo(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Accept either { "holo": {...} } or a bare HoloIR-like dict
    and persist it to the .holo store.

    Frontend (Glyph_Net_Browser) sends:
      POST /api/holo/import
      { "holo": { ... } }
    """
    try:
        holo_dict = body.get("holo") or body
        if not isinstance(holo_dict, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body must include a 'holo' object or be a holo dict.",
            )

        saved = save_holo_from_dict(holo_dict)

        # save_holo_from_dict might return a dict or a HoloIR; normalise
        if hasattr(saved, "__dict__"):
            saved = getattr(saved, "__dict__")

        return {"status": "ok", "holo": saved}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Holo import failed: {e}",
        )


# -------------------------------------------------------------------
# Container-scoped holo history / index
# -------------------------------------------------------------------


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


# -------------------------------------------------------------------
# Global holo_index search
# -------------------------------------------------------------------


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


# -------------------------------------------------------------------
# Holo from code (HST path)
# -------------------------------------------------------------------


class HoloFromCodePayload(BaseModel):
    source: str
    language: str
    container_id: Optional[str] = None
    tick: int = 0
    revision: int = 1


@router.post("/from_code")
def build_holo_from_code(payload: HoloFromCodePayload) -> Dict[str, Any]:
    """
    Minimal generic path for U3A:

      code/AST → HST → KG pack → .holo

    Right now we use a very simple HST (single 'program' node).
    Later you can swap in a real CodexAST → HST implementation.
    """
    container_id = payload.container_id or "devtools:code"

    try:
        hst = build_hst_from_source(
            source=payload.source,
            language=payload.language,
            container_id=container_id,
            tick=payload.tick,
            revision=payload.revision,
        )
        holo = build_holo_from_hst(
            hst,
            tick=payload.tick,
            frame="original",
            revision=payload.revision,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"holo_from_code_failed: {e}")

    return getattr(holo, "__dict__", holo)


# -------------------------------------------------------------------
# U3C — Rehydrate HST from .holo (+ KG)
# -------------------------------------------------------------------


@router.post("/rehydrate")
def rehydrate_from_holo(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Body: { "holo": { ...HoloIR-like dict... } }

    Uses rehydrate_hst_from_holo(...) which returns:
      { "hst": {...}, "kg": {...} }
    """
    try:
        holo = body.get("holo") or {}
        if not isinstance(holo, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Body must contain a 'holo' object.",
            )

        result = rehydrate_hst_from_holo(holo)

        # Ensure a status field for frontend convenience
        if isinstance(result, dict) and "status" not in result:
            result = {"status": "ok", **result}

        return result
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"rehydrate_from_holo_failed: {e}",
        )


class HoloImportPayload(BaseModel):
    holo: Dict[str, Any]

@router.post("/import")
def import_holo(payload: HoloImportPayload) -> Dict[str, Any]:
    """
    Accept a minimal HoloIR-like dict and persist it as a .holo snapshot.
    """
    saved = save_holo_from_dict(payload.holo)
    return saved

@router.get("/index/{container_id}")
def holo_index(container_id: str) -> Dict[str, Any]:
    """
    List all .holo snapshots for a container.
    """
    items = list_holos_for_container(container_id)
    return {"container_id": container_id, "items": items}

# -------------------------------------------------------------------
# Run .holo (U4: execution entrypoint)
# -------------------------------------------------------------------


class RunHoloRequest(BaseModel):
    holo: Dict[str, Any]
    input_ctx: Dict[str, Any] = {}
    mode: str = "qqc"


class RunHoloResponse(BaseModel):
    status: str
    message: Optional[str] = None
    container_id: str
    holo_id: Optional[str] = None
    tick: Optional[int] = None
    beams: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    output: Dict[str, Any]
    updated_holo: Optional[Dict[str, Any]] = None
    # NEW: tiny GHX packet (frames → nodes, edges)
    ghx: Optional[Dict[str, Any]] = None


@router.post("/run", response_model=RunHoloResponse)
async def run_holo_route(req: RunHoloRequest) -> RunHoloResponse:
    """
    Execute a Holo snapshot.

    Expected body:
      { "holo": {...}, "input_ctx": {...}, "mode": "qqc" }

    This is mounted under /api, so the full path is:
      POST /api/holo/run
    """
    try:
        result = await run_holo_snapshot(req.holo, req.input_ctx, req.mode)

        if isinstance(result, Dict) and "status" not in result:
            result["status"] = "ok"

        return RunHoloResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Holo run failed: {e}",
        )


# Optional alias so frontend can hit /api/holo/run_snapshot too
@router.post("/run_snapshot", response_model=RunHoloResponse)
async def run_snapshot_route(req: RunHoloRequest) -> RunHoloResponse:
    """
    Alias for /holo/run – same contract, different path.
    """
    return await run_holo_route(req)