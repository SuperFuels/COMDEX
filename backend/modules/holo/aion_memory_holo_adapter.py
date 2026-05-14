# backend/modules/holo/aion_memory_holo_adapter.py

"""
AION ↔ .holo adapter (memory side).

This module does NOT write .holo files yet.
It builds "HoloSeed" structures from MemoryEngine entries so that
a downstream exporter can turn them into full HoloIR snapshots.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List

from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.hexcore.memory_engine import MEMORY, MemoryEngine

DNA_SWITCH.register(__file__)

# Logical container id under which AION's personal memories will be grouped.
AION_MEMORY_CONTAINER_ID = "aion_memory::core"


@dataclass
class HoloSeed:
    """
    Minimal, backend-agnostic representation of a ".holo candidate".

    This is intentionally simple: it can be converted into a full HoloIR on demand
    without knowing the exact HoloIR Python model here.
    """

    seed_id: str
    container_id: str
    kind: str              # e.g. "memory_entry"
    label: str
    created_at: str
    tags: List[str]
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _seed_id_for_memory(entry: Dict[str, Any], container_id: str) -> str:
    """
    Deterministic-ish ID for a memory entry.

    Uses label + timestamp + small hash of content.
    """
    label = str(entry.get("label", "memory"))
    ts = str(entry.get("timestamp", datetime.utcnow().isoformat()))
    content = str(entry.get("content", ""))

    h = hashlib.sha256(
        f"{container_id}|{label}|{ts}|{content}".encode("utf-8")
    ).hexdigest()[:16]
    return f"holo-seed:{container_id}:{h}"


def memory_entry_to_holo_seed(
    entry: Dict[str, Any],
    container_id: str = AION_MEMORY_CONTAINER_ID,
) -> HoloSeed:
    """
    Convert a single MemoryEngine entry into a HoloSeed.
    """
    label = str(entry.get("label", "memory"))
    created_at = str(entry.get("timestamp", datetime.utcnow().isoformat()))
    tags = list(entry.get("milestone_tags") or entry.get("tags") or [])

    payload: Dict[str, Any] = {
        "label": label,
        "timestamp": created_at,
        "content": entry.get("content"),
        "source": entry.get("source", "MemoryEngine"),
    }

    # carry through glyph / scroll info if present
    for key in ("glyph", "glyph_tree", "scroll_preview", "scroll_tree"):
        if key in entry:
            payload[key] = entry[key]

    seed_id = _seed_id_for_memory(entry, container_id)

    return HoloSeed(
        seed_id=seed_id,
        container_id=container_id,
        kind="memory_entry",
        label=label,
        created_at=created_at,
        tags=tags,
        payload=payload,
    )


def recent_memory_to_holo_seeds(
    limit: int = 32,
    container_id: str = AION_MEMORY_CONTAINER_ID,
    only_milestones: bool = True,
) -> List[HoloSeed]:
    """
    Take the most recent MemoryEngine entries and wrap them as HoloSeeds.

    If only_milestones=True, filter to entries that carry milestone tags.
    """
    engine: MemoryEngine = MEMORY  # type: ignore[assignment]

    if hasattr(engine, "get_recent") and callable(getattr(engine, "get_recent")):
        entries = engine.get_recent(limit=limit)
    else:
        # fallback to full list if get_recent is missing
        entries = list(getattr(engine, "memory", []))[-limit:]

    seeds: List[HoloSeed] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if only_milestones:
            tags = entry.get("milestone_tags") or entry.get("tags") or []
            if not tags:
                continue
        seeds.append(memory_entry_to_holo_seed(entry, container_id=container_id))

    return seeds