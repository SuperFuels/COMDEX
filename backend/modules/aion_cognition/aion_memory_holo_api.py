# backend/modules/aion_cognition/aion_memory_holo_api.py
from __future__ import annotations

import copy
import logging
from typing import Any, Dict, Optional

from backend.modules.dna_chain.dna_switch import DNA_SWITCH
from backend.modules.holo.aion_holo_packer import pack_aion_memory_holo
from backend.modules.holo.aion_memory_container import (
    AION_MEMORY_CONTAINER_ID,
    load_latest_aion_memory_holo,
    save_aion_memory_holo,
)

DNA_SWITCH.register(__file__)
logger = logging.getLogger(__name__)


def read_holo(container_id: str = AION_MEMORY_CONTAINER_ID) -> Optional[Dict[str, Any]]:
    """
    High-level AION API: read latest memory .holo for the given container.

    For now we only support the single AION memory container.
    """
    if container_id != AION_MEMORY_CONTAINER_ID:
        raise ValueError(f"Unsupported container_id for AION memory holo: {container_id}")

    holo = load_latest_aion_memory_holo()
    if holo is None:
        logger.info("[AionMemoryHoloAPI] No existing holo snapshot for %s", container_id)
    return holo


def write_holo(
    container_id: str = AION_MEMORY_CONTAINER_ID,
    holo: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    High-level AION API: write a .holo snapshot for the memory container.

    - If no holo is provided, we build a fresh one via pack_aion_memory_holo().
    - Returns the holo with a small storage.metadata hint.
    """
    if container_id != AION_MEMORY_CONTAINER_ID:
        raise ValueError(f"Unsupported container_id for AION memory holo: {container_id}")

    if holo is None:
        holo = pack_aion_memory_holo()

    # Ensure we don't mutate caller data
    holo_copy: Dict[str, Any] = copy.deepcopy(holo)
    path = save_aion_memory_holo(holo_copy)

    storage_meta = holo_copy.setdefault("metadata", {}).setdefault("storage", {})
    storage_meta["container_id"] = container_id
    storage_meta["path"] = str(path)

    logger.info("[AionMemoryHoloAPI] Wrote holo snapshot for %s", container_id)
    return holo_copy


def rewrite_holo(
    container_id: str = AION_MEMORY_CONTAINER_ID,
    patch: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    High-level AION API: load latest holo, apply a shallow patch, and re-write.

    This is intentionally conservative: just top-level key updates, no deep merge.
    Returns the updated holo, or None if no prior snapshot exists.
    """
    base = read_holo(container_id)
    if base is None:
        return None

    patch = patch or {}
    updated = copy.deepcopy(base)
    for key, value in patch.items():
        updated[key] = value

    return write_holo(container_id, updated)