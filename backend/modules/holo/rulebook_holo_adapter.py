# backend/modules/holo/rulebook_holo_adapter.py

"""
AION ↔ .holo adapter (rulebook side).

Builds HoloSeed-like structures from RuleBookIndex entries so they can be
visualised as holograms later (e.g. "rulebook constellations").
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List

from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.aion_cognition.rulebook_index import RuleBookIndex

DNA_SWITCH.register(__file__)

# Logical container under which rulebook holograms live
RULEBOOK_CONTAINER_ID = "aion_rulebooks::core"
# Backwards-compat alias: some modules expect this name
AION_RULEBOOK_CONTAINER_ID = RULEBOOK_CONTAINER_ID


@dataclass
class RuleBookHoloSeed:
    """
    Lightweight, HoloSeed-style wrapper around a rulebook entry.

    This is intentionally backend-agnostic: a later exporter can
    turn this into a full HoloIR snapshot.
    """

    seed_id: str
    container_id: str
    kind: str  # always "rulebook"
    rulebook_id: str
    created_at: str
    updated_at: str
    usage_count: int
    tags: List[str]
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _seed_id_for_rulebook(rulebook_id: str, updated_at: float) -> str:
    """
    Deterministic-ish seed id: rulebook id + last updated timestamp.
    """
    raw = f"{rulebook_id}:{updated_at}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"holo-seed:rulebook:{rulebook_id}:{h}"


def rulebook_entry_to_holo_seed(
    rulebook_id: str,
    entry: Dict[str, Any],
    container_id: str = RULEBOOK_CONTAINER_ID,
) -> RuleBookHoloSeed:
    """
    Convert a single RuleBookIndex entry → RuleBookHoloSeed.
    """
    if not isinstance(entry, dict):
        raise TypeError(f"Rulebook entry for {rulebook_id!r} is not a dict")

    meta = entry.get("metadata", {}) or {}

    created_at = entry.get("created_at")
    updated_at = entry.get("updated_at", created_at or datetime.utcnow().timestamp())
    usage_count = int(entry.get("usage_count", 0))

    tags: List[str] = list(meta.get("tags", []))

    # Core payload: keep your existing shape so anything reading this doesn't break.
    payload: Dict[str, Any] = {
        "rulebook_id": rulebook_id,
        "name": meta.get("name"),
        "description": meta.get("description"),
        "domains": meta.get("domains"),
        "metrics": {
            "Φ_coherence": meta.get("Φ_coherence"),
            "Φ_entropy": meta.get("Φ_entropy"),
            "SQI": meta.get("SQI"),
        },
        "mutations": entry.get("mutations", []),
        "usage_count": usage_count,
        "last_used": entry.get("last_used"),
        "metadata": meta,
    }

    # Seed id is versioned by updated_at so changes produce new seeds.
    seed_id = _seed_id_for_rulebook(rulebook_id, float(updated_at or 0.0))

    # Normalise timestamps to ISO strings
    created_iso = (
        datetime.utcfromtimestamp(created_at).isoformat() + "Z"
        if isinstance(created_at, (int, float))
        else str(created_at or datetime.utcnow().isoformat())
    )
    updated_iso = (
        datetime.utcfromtimestamp(updated_at).isoformat() + "Z"
        if isinstance(updated_at, (int, float))
        else str(updated_at or created_iso)
    )

    return RuleBookHoloSeed(
        seed_id=seed_id,
        container_id=container_id,
        kind="rulebook",
        rulebook_id=rulebook_id,
        created_at=created_iso,
        updated_at=updated_iso,
        usage_count=usage_count,
        tags=tags,
        payload=payload,
    )


def all_rulebooks_to_holo_seeds(
    container_id: str = RULEBOOK_CONTAINER_ID,
) -> List[RuleBookHoloSeed]:
    """
    Wrap all currently registered rulebooks as RuleBookHoloSeed records.
    """
    index = RuleBookIndex()
    seeds: List[RuleBookHoloSeed] = []

    for rb_id, entry in index.rulebooks.items():
        if not isinstance(entry, dict):
            continue
        try:
            seeds.append(
                rulebook_entry_to_holo_seed(
                    rb_id,
                    entry,
                    container_id=container_id,
                )
            )
        except Exception as e:
            # best-effort; don't let one bad entry kill the whole set
            print(f"[RuleBookHoloAdapter] ⚠️ failed to adapt rulebook {rb_id}: {e}")

    return seeds