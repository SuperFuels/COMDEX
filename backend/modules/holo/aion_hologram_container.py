# backend/modules/holo/aion_hologram_container.py

"""
AION Memory Hologram Container spec.

Lightweight container that groups:
  - recent AION personal memory seeds
  - AION rulebook seeds
plus some simple layout metadata so the frontend/QFC can decide
how to arrange cards in the 3D field.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.holo.aion_memory_holo_adapter import (
    HoloSeed,
    AION_MEMORY_CONTAINER_ID,
)
from backend.modules.holo.rulebook_holo_adapter import (
    RuleBookHoloSeed,
    RULEBOOK_CONTAINER_ID,  # imported for symmetry/debug, even if not used yet
)

DNA_SWITCH.register(__file__)


@dataclass
class AionHologramContainer:
    container_id: str
    title: str
    description: str
    memory_seeds: List[Dict[str, Any]]
    rulebook_seeds: List[Dict[str, Any]]
    layout: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_aion_memory_container(
    memory_seeds: List[HoloSeed],
    rulebook_seeds: List[RuleBookHoloSeed],
) -> AionHologramContainer:
    """
    Build a logical "hologram container" for AION's internal memory field.

    This doesn't touch disk; it just shapes data that the HoloIR packer
    can embed into the .holo metadata block.
    """
    mem_dicts = [s.to_dict() for s in memory_seeds]
    rb_dicts = [s.to_dict() for s in rulebook_seeds]

    layout: Dict[str, Any] = {
        "kind": "aion_memory_constellation",
        "version": 1,
        "slots": {
            "memory": {
                "max_cards": 64,
                "placement": "inner_ring",
                "priority": "recent_milestones_first",
            },
            "rulebooks": {
                "max_cards": 16,
                "placement": "outer_ring",
                "priority": "usage_count_desc",
            },
        },
        "labels": {
            "memory": "AION recent memories",
            "rulebooks": "Active rulebooks",
        },
    }

    return AionHologramContainer(
        container_id=AION_MEMORY_CONTAINER_ID,
        title="AION Memory Field",
        description=(
            "Live constellation of AION's recent personal memories and "
            "active rulebooks, packed into a single hologram."
        ),
        memory_seeds=mem_dicts,
        rulebook_seeds=rb_dicts,
        layout=layout,
    )