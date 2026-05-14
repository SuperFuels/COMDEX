# backend/routes/holo_index_routes.py

"""
📚 Simple .holo registry / index API

For now this is a very lightweight, file-system based index:

  • Scans data/holo/**/*.holo.json
  • Optionally filters by:
      - container_id
      - tag (on any memory/rulebook seed)
      - seed (seed_id or payload.label)
  • Also supports a simple slug for AION memory:
      - /api/holo/index/aion-memory  →  container_id="aion_memory::core"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from backend.modules.dna_chain.dna_switch import DNA_SWITCH

DNA_SWITCH.register(__file__)

router = APIRouter(
    prefix="/api/holo",
    tags=["holo-index"],
)

HOLO_ROOT = Path("data/holo")


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────


def _iter_holo_files() -> List[Path]:
    if not HOLO_ROOT.exists():
        return []
    return list(HOLO_ROOT.rglob("*.holo.json"))


def _load_holo(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r") as f:
            return json.load(f)
    except Exception:
        return None


def _collect_seeds(holo: Dict[str, Any]) -> List[Dict[str, Any]]:
    meta = (holo.get("metadata") or {}).get("container") or {}
    mem = meta.get("memory_seeds") or []
    rules = meta.get("rulebook_seeds") or []
    return list(mem) + list(rules)


def _collect_tags_from_seeds(seeds: List[Dict[str, Any]]) -> List[str]:
    tags: List[str] = []
    for s in seeds:
        for t in s.get("tags") or []:
            if isinstance(t, str) and t not in tags:
                tags.append(t)
    return tags


def _seed_matches(seed_obj: Dict[str, Any], needle: str) -> bool:
    if not needle:
        return True

    if seed_obj.get("seed_id") == needle:
        return True

    payload = seed_obj.get("payload") or {}
    if payload.get("label") == needle:
        return True

    return False


# ──────────────────────────────────────────────
#  /api/holo/index
# ──────────────────────────────────────────────


@router.get("/index")
def list_holos(
    container_id: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    seed: Optional[str] = Query(None),
):
    """
    List .holo snapshots found under data/holo.

    Filters:
      • container_id: match holo['container_id']
      • tag: any seed.tag == tag
      • seed: match seed_id or payload.label
    """
    items: List[Dict[str, Any]] = []

    for p in _iter_holo_files():
        holo = _load_holo(p)
        if not holo:
            continue

        cid = holo.get("container_id")
        if container_id and cid != container_id:
            continue

        seeds = _collect_seeds(holo)
        tags = _collect_tags_from_seeds(seeds)

        if tag and tag not in tags:
            continue

        if seed:
            if not any(_seed_matches(s, seed) for s in seeds):
                continue

        mem_seeds = (holo.get("metadata") or {}).get("container", {}).get(
            "memory_seeds", []
        )
        rule_seeds = (holo.get("metadata") or {}).get("container", {}).get(
            "rulebook_seeds", []
        )

        items.append(
            {
                "holo_id": holo.get("holo_id"),
                "container_id": cid,
                "created_at": holo.get("created_at"),
                "path": str(p),
                "memory_seed_count": len(mem_seeds),
                "rulebook_seed_count": len(rule_seeds),
                "tags": tags,
            }
        )

    # newest first
    items.sort(
        key=lambda x: (x.get("created_at") or "", x.get("path") or ""),
        reverse=True,
    )

    return {
        "items": items,
        "total": len(items),
        "container_id": container_id,
        "tag": tag,
        "seed": seed,
    }


# ──────────────────────────────────────────────
#  /api/holo/index/{slug}
# ──────────────────────────────────────────────


@router.get("/index/{slug}")
def list_holos_by_slug(
    slug: str,
    tag: Optional[str] = Query(None),
    seed: Optional[str] = Query(None),
):
    """
    Convenience aliases like:

      /api/holo/index/aion-memory
        → container_id = "aion_memory::core"
    """
    if slug == "aion-memory":
        container_id = "aion_memory::core"
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown holo index slug",
        )

    base = list_holos(container_id=container_id, tag=tag, seed=seed)
    base["slug"] = slug
    return base