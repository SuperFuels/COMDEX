import json
import os
from typing import Dict, List

from backend.modules.hexcore.memory_engine import log_memory
from backend.modules.glyphos.symbolic_operator import is_entanglement_operator

# 🔒 UCS Entanglement database file
UCS_ENTANGLEMENTS_FILE = "backend/data/ucs_entanglements.json"


def _load_entanglements() -> Dict[str, List[str]]:
    """Load UCS container entanglement mappings."""
    if os.path.exists(UCS_ENTANGLEMENTS_FILE):
        with open(UCS_ENTANGLEMENTS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_entanglements(entanglements: Dict[str, List[str]]) -> None:
    """Save UCS container entanglement mappings."""
    with open(UCS_ENTANGLEMENTS_FILE, "w") as f:
        json.dump(entanglements, f, indent=2)


def entangle_containers(source_id: str, target_id: str) -> None:
    """Bidirectionally entangle two UCS containers."""
    entanglements = _load_entanglements()

    if source_id not in entanglements:
        entanglements[source_id] = []
    if target_id not in entanglements[source_id]:
        entanglements[source_id].append(target_id)

    if target_id not in entanglements:
        entanglements[target_id] = []
    if source_id not in entanglements[target_id]:
        entanglements[target_id].append(source_id)

    _save_entanglements(entanglements)
    log_memory("system", f"[UCS] Entangled containers: {source_id} ↔ {target_id}")


def get_entangled_containers(container_id: str) -> List[str]:
    """Return all UCS containers entangled with the given container."""
    entanglements = _load_entanglements()
    return entanglements.get(container_id, [])


def propagate_entangled_memory(container_id: str, memory: Dict) -> None:
    """Propagate memory events across entangled UCS containers."""
    # 🔄 Lazy import to break circular dependency
    from backend.modules.runtime.container_runtime import get_container_runtime

    runtime = get_container_runtime()
    targets = get_entangled_containers(container_id)

    for target_id in targets:
        data = runtime.get_container_data(target_id)
        if "entangled_memory" not in data:
            data["entangled_memory"] = []
        data["entangled_memory"].append(memory)
        runtime.save_container_data(target_id, data)


def register_entanglement(glyph_str: str, container_id: str) -> None:
    """Register entanglement relationships based on entanglement glyphs."""
    if is_entanglement_operator(glyph_str):
        for target in get_entangled_containers(container_id):
            entangle_containers(container_id, target)


def get_entangled_targets(container_id: str) -> List[str]:
    """Alias for retrieving entangled UCS targets."""
    return get_entangled_containers(container_id)


__all__ = [
    "entangle_containers",
    "get_entangled_containers",
    "propagate_entangled_memory",
    "register_entanglement",
    "get_entangled_targets",
]