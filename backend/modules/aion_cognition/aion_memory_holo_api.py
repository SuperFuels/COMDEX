# backend/modules/aion_cognition/aion_memory_holo_api.py
from __future__ import annotations

import json
import copy
import logging
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any, Dict, Optional

from backend.modules.dna_chain.dna_switch import DNA_SWITCH
from backend.modules.holo.aion_holo_packer import pack_aion_memory_holo
from backend.modules.holo.aion_memory_container import (
    AION_MEMORY_CONTAINER_ID,
    load_latest_aion_memory_holo,
    save_aion_memory_holo,
    get_aion_memory_container, 
)
from backend.modules.holo.holo_index import add_to_holo_index, HoloIndexEntry

DNA_SWITCH.register(__file__)
logger = logging.getLogger(__name__)


def _index_holo(holo: Dict[str, Any], path: Path) -> None:
    """
    Build a HoloIndexEntry from the holo + path and pass it to add_to_holo_index.
    """
    meta = holo.setdefault("metadata", {})
    container_meta = meta.get("container", {})

    memory_seeds = container_meta.get("memory_seeds", []) or []
    rulebook_seeds = container_meta.get("rulebook_seeds", []) or []

    tags: set[str] = set()
    for s in memory_seeds:
        for t in s.get("tags") or []:
            tags.add(t)
    for s in rulebook_seeds:
        for t in s.get("tags") or []:
            tags.add(t)

    record: Dict[str, Any] = {
        "holo_id": holo["holo_id"],
        "container_id": holo["container_id"],
        "created_at": holo.get("created_at"),
        "path": str(path),
        "tags": sorted(tags),
        "tick": holo.get("tick"),          # 👈 add this
        "revision": holo.get("revision"),  # 👈 and this
        "memory_seed_count": len(memory_seeds),
        "rulebook_seed_count": len(rulebook_seeds),
    }

    entry_kwargs: Dict[str, Any] = {}
    try:
        for f in dc_fields(HoloIndexEntry):
            name = f.name
            if name in record:
                entry_kwargs[name] = record[name]
        entry = HoloIndexEntry(**entry_kwargs)
        add_to_holo_index(entry)
    except Exception as e:
        logger.warning(
            "[AionMemoryHoloAPI] Failed to build/index HoloIndexEntry: %s", e
        )

def read_holo_by_id(holo_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a specific AION memory holo by its holo_id, e.g.:

      holo:aion_memory::t=4/v=1
    """
    if not holo_id.startswith("holo:aion_memory::"):
        raise ValueError(f"Unsupported holo_id for AION memory: {holo_id}")

    try:
        # tail = "t=4/v=1"
        tail = holo_id.split("::", 1)[1]
        t_part, v_part = tail.split("/", 1)  # "t=4", "v=1"

        tick_str = t_part.split("=", 1)[1]
        rev_str = v_part.split("=", 1)[1] if "=" in v_part else v_part.lstrip("v")

        tick = int(tick_str)
        revision = int(rev_str)
    except Exception as e:
        raise ValueError(f"Invalid holo_id format: {holo_id}") from e

    container = get_aion_memory_container()
    filename = f"t={tick}_v{revision}.holo.json"
    path: Path = container.root / filename

    if not path.exists():
        logger.info("[AionMemoryHoloAPI] No holo file for %s at %s", holo_id, path)
        return None

    with open(path, "r") as f:
        holo = json.load(f)

    logger.info("[AionMemoryHoloAPI] Loaded holo %s from %s", holo_id, path)
    return holo

def read_holo(
    container_id: str = AION_MEMORY_CONTAINER_ID,
) -> Optional[Dict[str, Any]]:
    """
    High-level AION API: read latest memory .holo for the given container.

    For now we only support the single AION memory container.
    """
    if container_id != AION_MEMORY_CONTAINER_ID:
        raise ValueError(
            f"Unsupported container_id for AION memory holo: {container_id}"
        )

    holo = load_latest_aion_memory_holo()
    if holo is None:
        logger.info(
            "[AionMemoryHoloAPI] No existing holo snapshot for %s", container_id
        )
    return holo


def write_holo(limit_memory: int = 64) -> Dict[str, Any]:
    """
    Build + persist a new AION memory .holo snapshot and index it.

    - Computes next tick based on existing files under the AION memory container
    - Uses revision=1 for now
    - Returns the holo with metadata.storage.path set
    """
    container = get_aion_memory_container()
    files = container.list_holo_files()

    # default: first snapshot
    next_tick = 0

    if files:
        # files are already sorted lexicographically in list_holo_files()
        # filenames look like: t=<tick>_v<rev>.holo.json
        last_name = files[-1].name  # e.g. "t=3_v1.holo.json"
        try:
            stem = Path(last_name).stem  # "t=3_v1.holo"
            tick_part = stem.split("_", 1)[0]  # "t=3"
            if tick_part.startswith("t="):
                tick_str = tick_part.split("=", 1)[1]
                last_tick = int(tick_str)
                next_tick = last_tick + 1
        except Exception as e:
            logger.warning(
                "[AionMemoryHoloAPI] Failed to parse tick from %s: %s",
                last_name,
                e,
            )

    revision = 1

    # Build holo with explicit tick/revision
    holo = pack_aion_memory_holo(
        limit_memory=limit_memory,
        tick=next_tick,
        revision=revision,
    )

    # Persist to disk
    path = save_aion_memory_holo(holo)

    # Ensure storage metadata is present on the holo
    meta = holo.setdefault("metadata", {})
    storage = meta.setdefault("storage", {})
    storage["container_id"] = AION_MEMORY_CONTAINER_ID
    storage["path"] = str(path)

    # Index it
    _index_holo(holo, path)

    logger.info(
        "[AionMemoryHoloAPI] Wrote holo snapshot for %s (tick=%s, rev=%s)",
        holo["container_id"],
        holo.get("tick"),
        holo.get("revision"),
    )

    return holo


def rewrite_holo(
    container_id: str = AION_MEMORY_CONTAINER_ID,
    patch: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    High-level AION API: load latest holo, apply a shallow patch, and re-write.

    - Only supports the AION memory container for now.
    - Shallow top-level updates only, no deep merge.
    - Re-saves the holo and updates the index entry.
    """
    if container_id != AION_MEMORY_CONTAINER_ID:
        raise ValueError(
            f"Unsupported container_id for AION memory holo: {container_id}"
        )

    base = read_holo(container_id)
    if base is None:
        return None

    patch = patch or {}
    updated = copy.deepcopy(base)
    for key, value in patch.items():
        updated[key] = value

    path = save_aion_memory_holo(updated)

    meta = updated.setdefault("metadata", {})
    storage = meta.setdefault("storage", {})
    storage["container_id"] = container_id
    storage["path"] = str(path)

    _index_holo(updated, path)

    logger.info(
        "[AionMemoryHoloAPI] Rewrote holo snapshot for %s (tick=%s, rev=%s)",
        updated["container_id"],
        updated.get("tick"),
        updated.get("revision"),
    )

    return updated