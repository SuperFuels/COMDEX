import json
import os
from typing import Dict, List

from backend.modules.hexcore.memory_engine import log_memory
from backend.modules.glyphos.symbolic_operator import is_entanglement_operator
from backend.modules.runtime.container_runtime import get_container_data, save_container_data  # ✅ FIXED

# 🔒 Entanglement database file
ENTANGLEMENTS_FILE = "backend/data/entanglements.json"

def _load_entanglements() -> Dict[str, List[str]]:
    if os.path.exists(ENTANGLEMENTS_FILE):
        with open(ENTANGLEMENTS_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_entanglements(entanglements: Dict[str, List[str]]) -> None:
    with open(ENTANGLEMENTS_FILE, "w") as f:
        json.dump(entanglements, f, indent=2)

def get_entangled_for(glyph: str) -> List[str]:
    entanglements = _load_entanglements()
    results = []
    for source, targets in entanglements.items():
        if glyph == source or glyph in targets:
            results.append(source if glyph != source else glyph)
            results.extend([t for t in targets if t != glyph])
    return list(set(results))

def entangle_containers(source_id: str, target_id: str) -> None:
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
    log_memory("system", f"Entangled containers: {source_id} ↔ {target_id}")

def get_entangled_containers(container_id: str) -> List[str]:
    entanglements = _load_entanglements()
    return entanglements.get(container_id, [])

def propagate_entangled_memory(container_id: str, memory: Dict) -> None:
    targets = get_entangled_containers(container_id)
    for target_id in targets:
        data = get_container_data(target_id)
        if "entangled_memory" not in data:
            data["entangled_memory"] = []
        data["entangled_memory"].append(memory)
        save_container_data(target_id, data)

def register_entanglement(glyph_str: str, container_id: str) -> None:
    if is_entanglement_operator(glyph_str):
        for target in get_entangled_containers(container_id):
            entangle_containers(container_id, target)

def get_entangled_targets(container_id: str) -> List[str]:
    return get_entangled_containers(container_id)

__all__ = [
    "get_entangled_for",
    "entangle_containers",
    "get_entangled_containers",
    "propagate_entangled_memory",
    "register_entanglement",
    "get_entangled_targets",
]