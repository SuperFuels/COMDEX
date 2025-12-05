# backend/routes/holo_aion_routes.py

"""
Admin / observability routes for AION ↔ .holo seeds & snapshots.

⚠️ These are *not* meant for general users.
They expose AION's internal memory + rulebook structures so DevTools /
master UI can visualize them as holograms.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.modules.dna_chain.dna_switch import DNA_SWITCH
from backend.modules.holo.aion_holo_memory import (
    get_aion_memory_holo_seeds,
    get_rulebook_holo_seeds,
    get_combined_holo_seeds,
)
from backend.modules.holo.aion_holo_packer import pack_aion_memory_holo

DNA_SWITCH.register(__file__)

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

AION_CONTAINER_ID = "aion_memory::core"
HOLO_ROOT = Path("data/holo")


router = APIRouter(
    prefix="/api/holo/aion",
    tags=["holo", "aion-internals"],
)

# ──────────────────────────────────────────────
#  Auth / admin guard (placeholder)
# ──────────────────────────────────────────────


def ensure_admin():
    """
    TODO: replace with real auth / role checks.

    For now this is just a stub so the dependency is explicit and easy to
    harden later (API key, JWT role, etc.).
    """
    return True


# ──────────────────────────────────────────────
#  Seeds (memory + rulebooks)
# ──────────────────────────────────────────────


@router.get(
    "/seeds/combined",
    summary="AION holo seeds (memory + rulebooks)",
    description=(
        "Returns a JSON-friendly combined view of AION's personal memory "
        "seeds and rulebook seeds, for DevTools / hologram viewers."
    ),
)
def read_combined_holo_seeds(
    limit_memory: int = 32,
    admin_ok: bool = Depends(ensure_admin),
):
    try:
        # { "memory": [...], "rulebooks": [...] }
        return get_combined_holo_seeds(limit_memory=limit_memory)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load AION holo seeds: {e}",
        )


@router.get(
    "/seeds/memory",
    summary="AION memory → HoloSeeds",
)
def read_memory_holo_seeds(
    limit: int = 32,
    admin_ok: bool = Depends(ensure_admin),
):
    try:
        seeds = get_aion_memory_holo_seeds(limit=limit)
        return [s.to_dict() for s in seeds]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load AION memory holo seeds: {e}",
        )


@router.get(
    "/seeds/rulebooks",
    summary="AION rulebooks → HoloSeeds",
)
def read_rulebook_holo_seeds(
    admin_ok: bool = Depends(ensure_admin),
):
    try:
        seeds = get_rulebook_holo_seeds()
        return [s.to_dict() for s in seeds]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load rulebook holo seeds: {e}",
        )


# ──────────────────────────────────────────────
#  Live hologram snapshot
# ──────────────────────────────────────────────


@router.get(
    "/snapshot",
    summary="Live AION memory hologram",
    description=(
        "Pack recent AION memory + rulebook seeds into a single HoloIR-shaped "
        "snapshot suitable for 3D field rendering."
    ),
)
def read_aion_memory_snapshot(
    limit_memory: int = 32,
    admin_ok: bool = Depends(ensure_admin),
):
    try:
        holo = pack_aion_memory_holo(limit_memory=limit_memory)
        return {"ok": True, "holo": holo}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build AION memory snapshot: {e}",
        )


# ──────────────────────────────────────────────
#  Helper: list .holo files for AION container
# ──────────────────────────────────────────────


def _list_aion_holos_internal(
    tag: Optional[str] = None,
    seed_id_contains: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Scan data/holo/aion_memory::core for *.holo.json and return a small
    summary list, optionally filtered by tag or seed substring.
    """

    container_dir = HOLO_ROOT / AION_CONTAINER_ID
    if not container_dir.exists():
        return []

    # newest first: reverse sort by filename (t=<tick>_v<rev>.holo.json)
    files = sorted(container_dir.glob("*.holo.json"), reverse=True)
    results: List[Dict[str, Any]] = []

    tag = tag or None
    seed_id_contains = (seed_id_contains or "").strip() or None
    seed_q = seed_id_contains.lower() if seed_id_contains else None

    for path in files:
        try:
            with open(path, "r") as f:
                holo = json.load(f)
        except Exception:
            continue

        meta_container = holo.get("metadata", {}).get("container", {})
        memory_seeds = meta_container.get("memory_seeds", []) or []
        rulebook_seeds = meta_container.get("rulebook_seeds", []) or []

        # --- tag filter ---
        if tag:
            found_tag = False

            for s in memory_seeds + rulebook_seeds:
                for t in s.get("tags", []) or []:
                    if t == tag or t.endswith(tag) or tag in t:
                        found_tag = True
                        break
                if found_tag:
                    break

            if not found_tag:
                continue

        # --- seed substring filter ---
        if seed_q:
            found_seed = False

            for s in memory_seeds + rulebook_seeds:
                sid = str(s.get("seed_id", "")).lower()
                label = str(s.get("label", "")).lower()
                if seed_q in sid or seed_q in label:
                    found_seed = True
                    break

            if not found_seed:
                continue

        results.append(
            {
                "holo_id": holo.get("holo_id"),
                "container_id": holo.get("container_id"),
                "tick": holo.get("tick"),
                "revision": holo.get("revision"),
                "created_at": holo.get("created_at"),
                "memory_seed_count": len(memory_seeds),
                "rulebook_seed_count": len(rulebook_seeds),
                "path": str(path),
            }
        )

        if len(results) >= limit:
            break

    return results


# ──────────────────────────────────────────────
#  Index / search over AION .holo snapshots
# ──────────────────────────────────────────────


@router.get(
    "/index",
    summary="Index of AION memory .holo snapshots",
    description=(
        "List AION memory .holo snapshots stored under data/holo/aion_memory::core. "
        "Supports simple filters by tag and seed id substring."
    ),
)
def read_aion_memory_holo_index(
    tag: str | None = Query(
        default=None,
        description="Filter snapshots that contain this tag on any seed.",
    ),
    seed: str | None = Query(
        default=None,
        description="Substring to match against seed_id or label.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=200,
        description="Maximum number of snapshots to return.",
    ),
    admin_ok: bool = Depends(ensure_admin),
):
    try:
        items = _list_aion_holos_internal(
            tag=tag,
            seed_id_contains=seed,
            limit=limit,
        )
        return {
            "container_id": AION_CONTAINER_ID,
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list AION holos: {e}",
        )