import os
import json
from typing import List
import hashlib
from datetime import datetime
from typing import Optional

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

from backend.modules.hexcore.memory_engine import MEMORY, store_memory, store_container_metadata
from backend.modules.consciousness.personality_engine import get_current_traits

# ✅ New mutation utilities
from backend.modules.dna_chain.dna_registry import register_proposal

# ✅ Safe SoulLaw Accessor (lazy, avoids circular import issues)
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator

_seen_dc_validate = set()

# ✅ Paths
DIMENSION_DIR = os.path.join(os.path.dirname(__file__), "../dimensions/containers")

# ✅ Path resolver for individual container files
def get_container_path(container_id: str) -> str:
    """Resolve full file path for a container ID like 'aion_start'."""
    filename = f"{container_id}.dc.json"
    return os.path.normpath(os.path.join(DIMENSION_DIR, "containers", filename))

# ✅ In-memory tracking (can be populated elsewhere)
CONTAINER_MEMORY = {}

def get_dc_path(container_id: str) -> str:
    """Return the filesystem path to a `.dc.json` container."""
    return os.path.join(DIMENSION_DIR, f"{container_id}.dc.json")

def compute_file_hash(path: str) -> str:
    """Compute SHA-256 hash for container file verification."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

# ✅ SoulLaw Container Check (hook point for container operations)
_soullaw_checked_ids = set()

def enforce_soul_law_on_container(container_data: dict, avatar_state: Optional[dict] = None) -> bool:
    """
    Validate a container and avatar state against SoulLaw before loading or mutation.
    Runs only once per container id/name per process.
    Returns True if allowed, raises PermissionError if blocked.
    """
    soul_law = get_soul_law_validator()

    # Determine stable key for deduplication
    cid = container_data.get("id") or container_data.get("name")
    if cid not in _soullaw_checked_ids:
        # Container-level morality check
        if not soul_law.validate_container(container_data):
            raise PermissionError(f"[🔒] SoulLaw: Container {cid} failed validation.")

        # Optional avatar state gate
        if avatar_state and not soul_law.validate_avatar(avatar_state):
            raise PermissionError(f"[🔒] SoulLaw: Avatar state blocked access for {cid}.")

        _soullaw_checked_ids.add(cid)
        print(f"[🔒] SoulLaw validated once for container: {cid}")
    return True
    
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
            raise PermissionError(f"[🔒] Access denied: Trait '{trait}' is {current}, required >= {min_value}")
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

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    validate_dimension(data)

    if data:
        store_memory({
            "role": "system",
            "label": "dimension_loaded",
            "content": f"Dimension '{container_id}' loaded.",
            "metadata": {
                "container_id": data.get("id", container_id),
                "cubes": list(data.get("cubes", {}).keys())
            }
        })

        entangled = data.get("entangled", [])
        if entangled:
            store_memory({
                "role": "system",
                "label": "entangled_links",
                "content": f"{container_id} is entangled with: {entangled}",
                "metadata": {
                    "container_id": container_id,
                    "entangled_with": entangled
                }
            })

    return data


# ✅ Define this at the global/module level
def get_entangled_links(container_id):
    container = load_dc_container(container_id)
    return container.get("entangled", [])

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
        
        # 🔗 Extract and store entanglement links
        entangled = container.get("entangled", [])
        if entangled:
            MEMORY.store({
                "role": "system",
                "label": "entangled_links",
                "content": f"{container['id']} is entangled with: {entangled}",
                "metadata": {
                    "container_id": container['id'],
                    "entangled_with": entangled
                }
            })

    return container

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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# Alias for compatibility with glyph_mutator
save_dimension_to_file = save_dimension

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

# --- NEW: microgrid injection helpers --------------------------------
from typing import List, Tuple, Dict, Any, Optional

def _coord_key(coord: Tuple[int, int, int]) -> str:
    """Normalize (x,y,z) to a stable microgrid dict key."""
    x, y, z = coord
    return f"{int(x)},{int(y)},{int(z)}"

from backend.modules.glyphvault.container_vault_integration import encrypt_and_embed_glyph_vault

def save_dc_container(container_id: str, container: Dict[str, Any]) -> None:
    """
    Persist a container to its .dc.json path.
    - Encrypts the glyph vault before saving.
    - Ensures directory path exists.
    """
    container = encrypt_and_embed_glyph_vault(container)  # Optional, but important if vaults are active

    path = get_dc_path(container_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(container, f, ensure_ascii=False, indent=2)

def inject_glyphs_into_universal_container_system(
    container_id: str,
    glyphs: List[Dict[str, Any]],
    placement: Optional[List[Tuple[int, int, int]]] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Inject one or many glyph entries into a UCS container microgrid.

    Args:
      container_id: target container id (resolved via get_dc_path)
      glyphs: list of glyph dicts, e.g. {"glyph":"🧠","tag":"reflect", ...}
      placement: optional list of (x,y,z) coords; if provided, must be same length as glyphs
      overwrite: if False, existing cells are left intact

    Returns:
      The updated container dict.
    """
    container = load_dc_container(container_id)
    microgrid = container.setdefault("microgrid", {})  # dict of "x,y,z" -> meta

    if placement:
        if len(placement) != len(glyphs):
            raise ValueError("placement length must match glyphs length")
        for g, coord in zip(glyphs, placement):
            key = _coord_key(coord)
            if not overwrite and key in microgrid:
                # skip existing cells unless overwrite=True
                continue
            microgrid[key] = g
    else:
        # No explicit coords: place sequentially into first free slots
        # We scan a small default lattice; adjust if you keep dims elsewhere.
        # You can also read dims from container.get("dims", [4,4,4]) if present.
        dims = container.get("dims", [4, 4, 4])
        X, Y, Z = map(int, dims)
        it = iter(glyphs)
        placed = 0
        for x in range(X):
            for y in range(Y):
                for z in range(Z):
                    if placed >= len(glyphs):
                        break
                    key = _coord_key((x, y, z))
                    if key not in microgrid or overwrite:
                        microgrid[key] = next(it)
                        placed += 1
                if placed >= len(glyphs):
                    break
            if placed >= len(glyphs):
                break
        if placed < len(glyphs):
            raise RuntimeError(
                f"Not enough free microgrid cells to place {len(glyphs)} glyph(s); placed {placed}."
            )

    save_dc_container(container_id, container)
    return container

def carve_glyph_cube(container_path, coord, glyph, meta: Optional[dict] = None):
    """Insert a glyph into a specific cube in a .dc container at the given coordinate with metadata."""
    if not os.path.exists(container_path):
        raise FileNotFoundError(f"Container not found at: {container_path}")

    with open(container_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cubes = data.setdefault("cubes", {})
    cube = cubes.setdefault(coord, {})
    cube["coord"] = [int(x) for x in coord.split(",")] if "," in coord else coord
    cube["glyph"] = glyph
    cube["timestamp"] = datetime.utcnow().isoformat()
    if meta:
        cube.update(meta)

    with open(container_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    MEMORY.store({
        "role": "system",
        "label": "glyph_carved",
        "content": f"Carved glyph '{glyph}' into {container_path} at {coord}",
        "metadata": {
            "coord": coord,
            "glyph": glyph,
            **(meta or {})
        }
    })

    print(f"[🪓] Glyph '{glyph}' carved at {coord} in {os.path.basename(container_path)}")

from backend.modules.glyphvault.container_vault_integration import decrypt_glyph_vault, encrypt_and_embed_glyph_vault

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

    # NEW: Decrypt glyph vault if present
    data = decrypt_glyph_vault(data)

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

    # ... rest unchanged ...
    return data

def load_dimension_by_file(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[dc_handler] File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        container = json.load(f)

    # NEW: Decrypt glyph vault if present
    container = decrypt_glyph_vault(container)

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

def inject_glyphs_into_container(container_filename: str, glyphs: List[dict], source: str = "manual") -> bool:
    """
    Inject a list of glyphs into the specified container file.
    The glyphs will be added sequentially to available empty slots.
    """
    path = get_dc_path(container_filename)
    if not os.path.exists(path):
        print(f"[❌] Container not found: {container_filename}")
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            container = json.load(f)

        inserted = 0
        for glyph in glyphs:
            placed = False
            for key, cube in container.get("cubes", {}).items():
                if cube.get("glyph") in [None, "", "⬛"]:
                    cube["glyph"] = glyph.get("symbol", "?")
                    cube["source"] = source
                    inserted += 1
                    placed = True
                    break
            if not placed:
                print("[⚠️] No empty cube slots available for glyph injection.")
                break

        with open(path, "w", encoding="utf-8") as f:
            json.dump(container, f, indent=2)

        print(f"[✅] Injected {inserted} glyph(s) into {container_filename}")
        return inserted > 0

    except Exception as e:
        print(f"[❌] Error injecting glyphs into container: {e}")
        return False