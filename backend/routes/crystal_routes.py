# backend/routes/crystal_routes.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.modules.dna_chain.dna_switch import DNA_SWITCH
from backend.modules.holo.crystal_container import (
    CrystalContainer,
    load_crystal_holo,
)

DNA_SWITCH.register(__file__)

router = APIRouter(
    prefix="/api/crystals",
    tags=["crystals"],
)


def ensure_admin() -> bool:
    # TODO: real auth
    return True


def _scan_crystals(scope: str) -> List[Dict[str, Any]]:
    container = CrystalContainer(scope=scope)
    paths = list(container.list_holo_paths())
    # newest first
    paths.sort(reverse=True)

    items: List[Dict[str, Any]] = []

    for path in paths:
        holo = load_crystal_holo(path)
        if not holo:
            continue

        meta = holo.get("metadata", {}) or {}
        motif_meta = meta.get("motif", {}) or {}

        motif_id = (
            motif_meta.get("motif_id")
            or meta.get("motif_id")
            or Path(path).stem
        )
        uri = motif_meta.get("uri") or meta.get("uri")

        pattern_strength = motif_meta.get("pattern_strength")
        sqi = motif_meta.get("SQI") or motif_meta.get("sqi")
        usage_count = motif_meta.get("usage_count") or meta.get("usage_count", 0)
        tags = motif_meta.get("tags") or meta.get("tags") or []

        items.append(
            {
                "motif_id": motif_id,
                "uri": uri,
                "tick": holo.get("tick"),
                "revision": holo.get("revision"),
                "created_at": holo.get("created_at"),
                "pattern_strength": pattern_strength,
                "SQI": sqi,
                "usage_count": usage_count,
                "tags": tags,
                "path": str(path),
            }
        )

    return items


@router.get(
    "/motifs",
    summary="List crystal motifs",
    description=(
        "Scan data/crystals/<scope> for motif-*.holo.json and return "
        "a summary list."
    ),
)
def list_crystal_motifs(
    scope: str = Query(
        default="user/devtools",
        description="Logical crystal scope, e.g. 'user/devtools'.",
    ),
    admin_ok: bool = Depends(ensure_admin),
):
    try:
      items = _scan_crystals(scope)
      return {
          "scope": scope,
          "count": len(items),
          "items": items,
      }
    except Exception as e:
      raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail=f"Failed to list crystals: {e}",
      )


@router.get(
    "/motifs/{motif_id}",
    summary="Load a specific crystal motif holo",
)
def get_crystal_motif(
    motif_id: str,
    scope: str = Query(
        default="user/devtools",
        description="Logical crystal scope, e.g. 'user/devtools'.",
    ),
    admin_ok: bool = Depends(ensure_admin),
):
    container = CrystalContainer(scope=scope)
    for path in container.list_holo_paths():
        stem = path.stem  # motif-0003__t=3_v1
        if motif_id in stem:
            holo = load_crystal_holo(path)
            if not holo:
                break
            return {"holo": holo}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Crystal motif not found: {motif_id} (scope={scope})",
    )