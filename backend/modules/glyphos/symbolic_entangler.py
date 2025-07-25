# File: backend/modules/glyphos/symbolic_entangler.py

from typing import Dict, List
from backend.modules.hexcore.memory_engine import MemoryEngine

# Runtime entanglement registries (in-memory)
entangled_glyphs: List[Dict[str, str]] = []
entangled_containers: Dict[str, List[str]] = {}


def entangle_glyphs(g1: str, g2: str) -> Dict[str, str]:
    """
    Symbolically entangles two glyphs. Future actions on one may influence the other.
    """
    pair = {"glyph1": g1, "glyph2": g2}
    entangled_glyphs.append(pair)
    return pair


def get_entangled_for(glyph: str) -> List[str]:
    """
    Returns all glyphs entangled with the given one.
    """
    return [
        p["glyph2"] if p["glyph1"] == glyph else p["glyph1"]
        for p in entangled_glyphs
        if glyph in (p["glyph1"], p["glyph2"])
    ]


def entangle_containers(c1: str, c2: str) -> None:
    """
    Registers symbolic entanglement between two containers.
    """
    entangled_containers.setdefault(c1, [])
    entangled_containers.setdefault(c2, [])

    if c2 not in entangled_containers[c1]:
        entangled_containers[c1].append(c2)
    if c1 not in entangled_containers[c2]:
        entangled_containers[c2].append(c1)


def get_entangled_containers(container_id: str) -> List[str]:
    """
    Gets containers entangled with the given one.
    """
    return entangled_containers.get(container_id, [])


def propagate_entangled_memory(source_id: str, memory: dict, tag: str = "↔ entangled") -> None:
    """
    Propagates memory to all containers symbolically entangled with source_id.
    """
    for target_id in get_entangled_containers(source_id):
        MemoryEngine().store(target_id, memory, tag=tag)


__all__ = [
    "entangle_glyphs",
    "get_entangled_for",
    "entangle_containers",
    "get_entangled_containers",
    "propagate_entangled_memory",
]