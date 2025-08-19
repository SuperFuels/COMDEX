import json
import os
from typing import Dict, List

from backend.modules.hexcore.memory_engine import log_memory
from backend.modules.glyphos.symbolic_operator import is_entanglement_operator

def get_runtime():
    from backend.modules.runtime.container_runtime import get_container_runtime
    return get_container_runtime

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
    from backend.modules.runtime.container_runtime import get_container_runtime
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
    runtime = get_runtime()  # ✅ Access the global runtime instance
    targets = get_entangled_containers(container_id)

    for target_id in targets:
        data = runtime.get_container_data(target_id)  # ✅ Use runtime method
        if "entangled_memory" not in data:
            data["entangled_memory"] = []
        data["entangled_memory"].append(memory)
        runtime.save_container_data(target_id, data)  # ✅ Use runtime method

def register_entanglement(glyph_str: str, container_id: str) -> None:
    if is_entanglement_operator(glyph_str):
        for target in get_entangled_containers(container_id):
            entangle_containers(container_id, target)

def get_entangled_targets(container_id: str) -> List[str]:
    return get_entangled_containers(container_id)

# ✅ Alias for backward compatibility with GHX and older modules
def get_entangled_links(container_id: str) -> List[str]:
    """Alias for backward compatibility – forwards to get_entangled_targets."""
    return get_entangled_targets(container_id)

__all__ = [
    "get_entangled_for",
    "entangle_containers",
    "get_entangled_containers",
    "propagate_entangled_memory",
    "register_entanglement",
    "get_entangled_targets",
    "get_entangled_links",  # ✅ Added alias export
]

# ─────────────────────────────────────────────────────────────────────────────
# 🔗 Minimal public entanglement API (used by glyphnet_terminal)
#   - In-memory registry
#   - Thread-safe
#   - Backwards-compatible names: entangle_glyphs / disentangle / get_entanglements
# ─────────────────────────────────────────────────────────────────────────────
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
import time
import uuid
from threading import RLock

@dataclass
class Entanglement:
    id: str
    a: str
    b: str
    strength: float
    created_ts: float
    meta: Dict[str, Any]

# Global registry (process-local)
__ENT_REGISTRY: Dict[str, Entanglement] = {}
__ENT_INDEX: Dict[Tuple[str, str], str] = {}
__ENT_LOCK = RLock()

def _norm_pair(a: str, b: str) -> Tuple[str, str]:
    return tuple(sorted((str(a), str(b))))

def entangle_glyphs(a: str, b: str, *, strength: float = 1.0, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create (or refresh) an entanglement between two glyph ids/labels.
    Returns a dict for easy JSON logging.
    """
    with __ENT_LOCK:
        pair = _norm_pair(a, b)
        ent_id = __ENT_INDEX.get(pair)
        now = time.time()
        if ent_id and ent_id in __ENT_REGISTRY:
            ent = __ENT_REGISTRY[ent_id]
            # refresh strength and meta (non-destructive merge)
            ent.strength = float(strength)
            if meta:
                ent.meta.update(meta)
        else:
            ent = Entanglement(
                id=str(uuid.uuid4()),
                a=pair[0],
                b=pair[1],
                strength=float(strength),
                created_ts=now,
                meta=dict(meta or {}),
            )
            __ENT_REGISTRY[ent.id] = ent
            __ENT_INDEX[pair] = ent.id
        return asdict(ent)

def disentangle(a: str, b: str) -> bool:
    """Remove an entanglement between a and b if present."""
    with __ENT_LOCK:
        pair = _norm_pair(a, b)
        ent_id = __ENT_INDEX.pop(pair, None)
        if ent_id and ent_id in __ENT_REGISTRY:
            __ENT_REGISTRY.pop(ent_id, None)
            return True
        return False

def entanglement_strength(a: str, b: str) -> float:
    """Get current strength (0.0 if not entangled)."""
    with __ENT_LOCK:
        pair = _norm_pair(a, b)
        ent_id = __ENT_INDEX.get(pair)
        if ent_id and ent_id in __ENT_REGISTRY:
            return __ENT_REGISTRY[ent_id].strength
        return 0.0

def get_entanglements() -> List[Dict[str, Any]]:
    """List all active entanglements as dicts."""
    with __ENT_LOCK:
        return [asdict(e) for e in __ENT_REGISTRY.values()]

# Make sure these names are exported for star-imports or explicit imports
try:
    __all__  # may or may not exist
except NameError:
    __all__ = []
__all__ += [
    "entangle_glyphs",
    "disentangle",
    "entanglement_strength",
    "get_entanglements",
]