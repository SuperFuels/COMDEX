import os
import json
import time
from typing import Optional, Dict, List, Set
from collections import defaultdict

from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.glyphnet.glyphnet_packet import push_symbolic_packet

ENTANGLEMENT_FILE = "data/entanglement_links.json"
_entanglement_graph: Dict[str, Set[str]] = defaultdict(set)


def _load_entanglement_graph():
    if os.path.exists(ENTANGLEMENT_FILE):
        try:
            with open(ENTANGLEMENT_FILE, "r") as f:
                data = json.load(f)
                for source, targets in data.items():
                    _entanglement_graph[source] = set(targets)
            print(f"🔗 Loaded entanglement graph: {len(_entanglement_graph)} containers.")
        except Exception as e:
            print(f"⚠️ Failed to load entanglement data: {e}")


def _save_entanglement_graph():
    try:
        serializable = {k: list(v) for k, v in _entanglement_graph.items()}
        os.makedirs(os.path.dirname(ENTANGLEMENT_FILE), exist_ok=True)
        with open(ENTANGLEMENT_FILE, "w") as f:
            json.dump(serializable, f, indent=2)
        print(f"✅ Saved entanglement links to disk.")
    except Exception as e:
        print(f"🚨 Failed to save entanglement graph: {e}")


def get_entangled_links_for_container(container_id: str) -> List[str]:
    return list(_entanglement_graph.get(container_id, []))


def get_all_entanglements() -> Dict[str, List[str]]:
    return {k: list(v) for k, v in _entanglement_graph.items()}


def entangle_glyphs(
    glyph: str,
    container_a_id: str,
    container_b_id: Optional[str] = None,
    sender: str = "system",
    push: bool = True
) -> dict:
    """
    Symbolically entangle two containers (or one container's internal coordinate).
    """
    # ✅ Lazy imports to prevent circular dependency
    from backend.modules.runtime.container_runtime import save_container_data, get_container_by_id
    from backend.routes.ws.glyphnet_ws import push_entanglement_update

    timestamp = time.time()
    if not container_b_id:
        container_b_id = container_a_id

    memory_entry = {
        "type": "entanglement",
        "glyph": glyph,
        "from": container_a_id,
        "to": container_b_id,
        "timestamp": timestamp,
        "sender": sender,
    }

    # Log memory
    store_memory(memory_entry)

    # Update container metadata
    container_a = get_container_by_id(container_a_id)
    container_b = get_container_by_id(container_b_id)

    for container, other_id in [(container_a, container_b_id), (container_b, container_a_id)]:
        if container:
            entangled = container.setdefault("entangled", [])
            if other_id not in entangled and other_id != container.get("id"):
                entangled.append(other_id)

    save_container_data(container_a_id)
    save_container_data(container_b_id)

    # Update entanglement graph
    _entanglement_graph[container_a_id].add(container_b_id)
    _entanglement_graph[container_b_id].add(container_a_id)
    _save_entanglement_graph()

    # WebSocket broadcast (lazy import used)
    push_entanglement_update(container_a_id, container_b_id)

    if push:
        push_symbolic_packet({
            "type": "glyph_push",
            "sender": sender,
            "payload": memory_entry,
            "timestamp": timestamp,
        })

    print(f"↔️ Entangled: {container_a_id} ↔ {container_b_id}")
    return memory_entry


# Load entanglement graph on startup
_load_entanglement_graph()