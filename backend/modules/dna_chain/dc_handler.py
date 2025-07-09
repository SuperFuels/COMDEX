import os
import json
import hashlib
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

from backend.modules.hexcore.memory_engine import MEMORY, store_memory, store_container_metadata
from backend.modules.consciousness.personality_engine import get_current_traits

# ✅ New mutation utilities
from backend.modules.dna_chain.dna_registry import register_proposal

# ✅ Paths
DIMENSION_DIR = os.path.join(os.path.dirname(__file__), "../dimensions/containers")

# ✅ Path resolver for individual container files
def get_container_path(container_id: str) -> str:
    """Resolve full file path for a container ID like 'aion_start'."""
    filename = f"{container_id}.dc.json"
    return os.path.normpath(os.path.join(DIMENSION_DIR, "containers", filename))

# ✅ In-memory tracking (can be populated elsewhere)
CONTAINER_MEMORY = {}

def get_dc_path(container_id):
    return os.path.join(DIMENSION_DIR, f"{container_id}.dc.json")

def compute_file_hash(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def validate_dimension(data):
    required_fields = ["id", "name", "description", "created_on", "dna_switch"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"[⚠️] Missing required field: {field}")
    return True

def check_gate_lock(data):
    gate = data.get("gate")
    if not gate:
        return True
    required_traits = gate.get("required_traits", {})
    current_traits = get_current_traits()
    for trait, min_value in required_traits.items():
        current = current_traits.get(trait, 0)
        if current < min_value:
            raise PermissionError(f"[🔒] Access denied: Trait '{trait}' is {current}, required ≥ {min_value}")
    return True

def load_dimension(container_id):
    path = get_dc_path(container_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"[❌] Dimension container '{container_id}' not found at {path}")

    try:
        original_hash = compute_file_hash(path)
    except Exception as e:
        store_memory({
            "type": "tamper_alert",
            "role": "system",
            "content": f"[❌] Could not read container file: {container_id}: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        })
        raise

    with open(path, "r") as f:
        data = json.load(f)

    validate_dimension(data)

    try:
        check_gate_lock(data)
    except PermissionError as e:
        store_memory({
            "type": "access_denied",
            "role": "system",
            "content": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        raise

    store_container_metadata(data)

    print(f"[📦] Loaded dimension: {data['name']} (ID: {data['id']})")

    # 🖁️ Auto teleport logic
    navigation = data.get("navigation", {})
    next_target = navigation.get("next")
    auto = navigation.get("auto_teleport", False)

    if auto and next_target:
        from backend.modules.dna_chain.teleport import teleport
        print(f"[🤝] Auto-teleporting to next dimension: {next_target}")
        teleport(container_id, next_target, reason="auto_teleport")
        store_memory({
            "type": "teleport_event",
            "source": container_id,
            "destination": next_target,
            "trigger": "auto_teleport",
            "timestamp": datetime.utcnow().isoformat()
        })

    # 🧠 Store teleport event as memory
    MEMORY.store({
        "role": "system",
        "label": "container_loaded",
        "content": f"AION teleported to container: {data['id']}",
        "metadata": {
            "container_id": data['id'],
            "cubes": list(data.get('cubes', {}).keys())
        }
    })

    return data

def load_dimension_by_file(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[dc_handler] File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        container = json.load(f)

    if "id" not in container:
        raise ValueError(f"[dc_handler] Invalid container file (missing 'id'): {file_path}")

    DNA_SWITCH.register(file_path)
    store_container_metadata(container)

    if container:
        MEMORY.store({
            "role": "system",
            "label": "container_loaded",
            "content": f"AION teleported to container: {container['id']}",
            "metadata": {
                "container_id": container['id'],
                "cubes": list(container.get('cubes', {}).keys())
            }
        })

    return container

def load_dimension_by_id(container_id: str):
    return load_dimension(container_id)

# 🔁 Utilities

def list_stored_containers():
    return MEMORY.list_stored_containers()

def load_dc_container(container_id):
    path = get_dc_path(container_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Container '{container_id}' not found at path: {path}")
    with open(path, "r", encoding="utf-8") as f:
        container = json.load(f)

    if container:
        MEMORY.store({
            "role": "system",
            "label": "container_loaded",
            "content": f"AION teleported to container: {container['id']}",
            "metadata": {
                "container_id": container['id'],
                "cubes": list(container.get('cubes', {}).keys())
            }
        })

    return container

def save_dc_container(container_id, data):
    path = get_dc_path(container_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def list_cubes(container_id):
    container = load_dc_container(container_id)
    return list(container.get("cubes", {}).keys())

def get_cube(container_id, cube_key):
    container = load_dc_container(container_id)
    return container.get("cubes", {}).get(cube_key, {})

def get_wormholes(container_id):
    container = load_dc_container(container_id)
    return container.get("wormholes", {})

def resolve_wormhole(container_id, wormhole_id):
    wormholes = get_wormholes(container_id)
    return wormholes.get(wormhole_id)

def save_dimension(path: str, data: dict):
    """
    Saves a container (.dc) file to disk with the given data dictionary.
    Keys should be strings like "x,y,z[,layer]" and values should be glyphs or metadata.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def apply_style_to_cube(container_id, cube_key, layer, material, area):
    container = load_dc_container(container_id)
    cube = container.setdefault("cubes", {}).setdefault(cube_key, {})
    layers = cube.setdefault("layers", {})
    layer_list = layers.setdefault(layer, [])
    layer_list.append({
        "material": material,
        "area": area
    })
    save_dc_container(container_id, container)

def list_available_containers():
    stored = set(list_stored_containers())
    containers = []

    for file in os.listdir(DIMENSION_DIR):
        if file.endswith(".dc.json"):
            container_id = file.replace(".dc.json", "")
            containers.append({
                "id": container_id,
                "loaded": container_id in stored,
                "in_memory": container_id in CONTAINER_MEMORY
            })

    return containers

def handle_object_interaction(obj_id, current_container):
    data = CONTAINER_MEMORY.get(current_container)
    if not data:
        raise ValueError("Container not loaded in memory")

    for obj in data.get("objects", []):
        if obj.get("id") == obj_id and obj.get("type") == "teleporter":
            target = obj.get("teleport_to")
            if target:
                print(f"[🔀] Teleporting via object '{obj_id}' to '{target}'")
                from backend.modules.dna_chain.teleport import teleport
                try:
                    teleport(current_container, target, reason=f"object_trigger:{obj_id}")
                    store_memory({
                        "type": "teleport_event",
                        "source": current_container,
                        "destination": target,
                        "trigger": f"object:{obj_id}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    return True
                except Exception as e:
                    store_memory({
                        "type": "teleport_failed",
                        "source": current_container,
                        "attempted_target": target,
                        "trigger": f"object:{obj_id}",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
    return False

def handle_navigation_teleport(current_container, target_id):
    data = CONTAINER_MEMORY.get(current_container)
    if not data:
        raise ValueError("Container not loaded in memory")

    routes = data.get("navigation", {}).get("routes", [])
    if target_id in routes:
        print(f"[🤍] Navigating from '{current_container}' to '{target_id}' via routes")
        from backend.modules.dna_chain.teleport import teleport
        try:
            teleport(current_container, target_id, reason="navigation_route")
            store_memory({
                "type": "teleport_event",
                "source": current_container,
                "destination": target_id,
                "trigger": "navigation_route",
                "timestamp": datetime.utcnow().isoformat()
            })
            return True
        except Exception as e:
            store_memory({
                "type": "teleport_failed",
                "source": current_container,
                "attempted_target": target_id,
                "trigger": "navigation_route",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    return False

def list_containers_with_memory_status():
    containers = []
    for filename in os.listdir(DIMENSION_DIR):
        if filename.endswith(".dc.json"):
            container_id = filename.replace(".dc.json", "")
            in_memory = container_id in CONTAINER_MEMORY
            containers.append({
                "id": container_id,
                "in_memory": in_memory
            })
    return containers