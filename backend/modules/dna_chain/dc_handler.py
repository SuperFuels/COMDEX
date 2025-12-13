# backend/modules/dna_chain/dc_handler.py

import os
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

from backend.modules.hexcore.memory_engine import (
    MEMORY,
    store_memory,
    store_container_metadata,
)
from backend.modules.consciousness.personality_engine import get_current_traits

# ✅ New mutation utilities (kept for callers that import it from here)
from backend.modules.dna_chain.dna_registry import register_proposal  # noqa: F401

# ✅ Safe SoulLaw Accessor (lazy, avoids circular import issues)
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator

# ✅ Glyph vault integration (save encrypts; load must decrypt)
from backend.modules.glyphvault.container_vault_integration import (
    decrypt_glyph_vault,
    encrypt_and_embed_glyph_vault,
)

_seen_dc_validate = set()

# ✅ Paths
# This file lives in backend/modules/dna_chain/ -> containers live in backend/modules/dimensions/containers/
DIMENSION_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "dimensions", "containers")
)

# ✅ In-memory tracking (can be populated elsewhere)
CONTAINER_MEMORY: Dict[str, Dict[str, Any]] = {}

# -------------------------------------------------------------------------
# Path helpers
# -------------------------------------------------------------------------
def get_dc_path(container_id: str) -> str:
    """Return the filesystem path to a `.dc.json` container."""
    return os.path.join(DIMENSION_DIR, f"{container_id}.dc.json")


def get_container_path(container_id: str) -> str:
    """Back-compat alias for callers that used get_container_path()."""
    return get_dc_path(container_id)


# -------------------------------------------------------------------------
# Integrity helpers
# -------------------------------------------------------------------------
def compute_file_hash(path: str) -> str:
    """Compute SHA-256 hash for container file verification."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


# -------------------------------------------------------------------------
# SoulLaw + validation
# -------------------------------------------------------------------------
_soullaw_checked_ids = set()


def enforce_soul_law_on_container(
    container_data: dict, avatar_state: Optional[dict] = None
) -> bool:
    """
    Validate a container + optional avatar state against SoulLaw before load/mutation.
    Runs only once per container id/name per process.
    """
    soul_law = get_soul_law_validator()

    cid = container_data.get("id") or container_data.get("name")
    if cid not in _soullaw_checked_ids:
        if not soul_law.validate_container(container_data):
            raise PermissionError(f"[🔒] SoulLaw: Container {cid} failed validation.")

        if avatar_state and not soul_law.validate_avatar(avatar_state):
            raise PermissionError(f"[🔒] SoulLaw: Avatar state blocked access for {cid}.")

        _soullaw_checked_ids.add(cid)
        print(f"[🔒] SoulLaw validated once for container: {cid}")

    return True


def validate_dimension(data: dict) -> bool:
    required_fields = ["id", "name", "description", "created_on", "dna_switch"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"[⚠️] Missing required field: {field}")
    return True


def check_gate_lock(data: dict) -> bool:
    gate = data.get("gate")
    if not gate:
        return True
    required_traits = gate.get("required_traits", {})
    current_traits = get_current_traits()
    for trait, min_value in required_traits.items():
        current = current_traits.get(trait, 0)
        if current < min_value:
            raise PermissionError(
                f"[🔒] Access denied: Trait '{trait}' is {current}, required >= {min_value}"
            )
    return True


# -------------------------------------------------------------------------
# Core load/save
# -------------------------------------------------------------------------
def load_dc_container(container_id: str) -> Dict[str, Any]:
    """
    Low-level container JSON load:
    - Reads .dc.json
    - Decrypts glyph vault if present (because save_dc_container encrypts)
    - Emits basic MEMORY telemetry
    """
    path = get_dc_path(container_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Container '{container_id}' not found at path: {path}")

    with open(path, "r", encoding="utf-8") as f:
        container = json.load(f)

    # ✅ Always decrypt on load (idempotent if no vault present)
    try:
        container = decrypt_glyph_vault(container)
    except Exception:
        # never break load if vault integration changes
        pass

    if container:
        MEMORY.store(
            {
                "role": "system",
                "label": "container_loaded",
                "content": f"AION teleported to container: {container.get('id', container_id)}",
                "metadata": {
                    "container_id": container.get("id", container_id),
                    "cubes": list((container.get("cubes") or {}).keys()),
                },
            }
        )

        entangled = container.get("entangled", [])
        if entangled:
            MEMORY.store(
                {
                    "role": "system",
                    "label": "entangled_links",
                    "content": f"{container.get('id', container_id)} is entangled with: {entangled}",
                    "metadata": {
                        "container_id": container.get("id", container_id),
                        "entangled_with": entangled,
                    },
                }
            )

    return container


def load_dimension(container_id: str) -> Dict[str, Any]:
    """
    High-level container load:
    - Loads + decrypts via load_dc_container()
    - Validates schema + gate lock
    - Stores metadata + optional entanglement telemetry
    - (Keeps your prior memory/log behavior in one reachable function)
    """
    path = get_dc_path(container_id)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"[❌] Dimension container '{container_id}' not found at {path}"
        )

    # Hash check (best-effort telemetry)
    try:
        original_hash = compute_file_hash(path)
    except Exception as e:
        store_memory(
            {
                "type": "tamper_alert",
                "role": "system",
                "content": f"[❌] Could not read container file: {container_id}: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        raise

    data = load_dc_container(container_id)

    validate_dimension(data)
    check_gate_lock(data)
    store_container_metadata(data)

    # Extra telemetry (kept)
    store_memory(
        {
            "role": "system",
            "label": "dimension_loaded",
            "content": f"Dimension '{container_id}' loaded.",
            "metadata": {
                "container_id": data.get("id", container_id),
                "cubes": list((data.get("cubes") or {}).keys()),
                "sha256": original_hash,
            },
        }
    )

    print(f"[📦] Loaded dimension: {data['name']} (ID: {data['id']})")
    return data


def get_entangled_links(container_id: str) -> List[str]:
    """Return entangled container IDs for a given container."""
    container = load_dc_container(container_id)
    ent = container.get("entangled", [])
    return ent if isinstance(ent, list) else []


def load_dimension_by_id(container_id: str) -> Dict[str, Any]:
    return load_dimension(container_id)


def load_dimension_by_file(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[dc_handler] File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        container = json.load(f)

    # ✅ Decrypt glyph vault if present
    try:
        container = decrypt_glyph_vault(container)
    except Exception:
        pass

    if "id" not in container:
        raise ValueError(
            f"[dc_handler] Invalid container file (missing 'id'): {file_path}"
        )

    DNA_SWITCH.register(file_path)
    validate_dimension(container)
    check_gate_lock(container)
    store_container_metadata(container)

    MEMORY.store(
        {
            "role": "system",
            "label": "container_loaded",
            "content": f"AION teleported to container: {container['id']}",
            "metadata": {
                "container_id": container["id"],
                "cubes": list((container.get("cubes") or {}).keys()),
            },
        }
    )

    return container


def save_dimension(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# Alias for compatibility with glyph_mutator
save_dimension_to_file = save_dimension


def save_dc_container(container_id: str, container: Dict[str, Any]) -> None:
    """
    Persist a container to its .dc.json path.
    - Encrypts the glyph vault before saving.
    - Ensures directory path exists.
    """
    try:
        container = encrypt_and_embed_glyph_vault(container)
    except Exception:
        pass

    path = get_dc_path(container_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(container, f, ensure_ascii=False, indent=2)


# -------------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------------
def list_stored_containers():
    return MEMORY.list_stored_containers()


def list_cubes(container_id: str) -> List[str]:
    container = load_dc_container(container_id)
    return list((container.get("cubes") or {}).keys())


def get_cube(container_id: str, cube_key: str) -> Dict[str, Any]:
    container = load_dc_container(container_id)
    return (container.get("cubes") or {}).get(cube_key, {})


def get_wormholes(container_id: str) -> Dict[str, Any]:
    container = load_dc_container(container_id)
    return container.get("wormholes", {}) or {}


def resolve_wormhole(container_id: str, wormhole_id: str):
    wormholes = get_wormholes(container_id)
    return wormholes.get(wormhole_id)


def apply_style_to_cube(container_id: str, cube_key: str, layer: str, material: str, area: Any):
    container = load_dc_container(container_id)
    cube = (container.setdefault("cubes", {})).setdefault(cube_key, {})
    layers = cube.setdefault("layers", {})
    layer_list = layers.setdefault(layer, [])
    layer_list.append({"material": material, "area": area})
    save_dc_container(container_id, container)


def list_available_containers():
    stored = set(list_stored_containers())
    containers = []

    if not os.path.isdir(DIMENSION_DIR):
        return containers

    for file in os.listdir(DIMENSION_DIR):
        if file.endswith(".dc.json"):
            container_id = file.replace(".dc.json", "")
            containers.append(
                {
                    "id": container_id,
                    "loaded": container_id in stored,
                    "in_memory": container_id in CONTAINER_MEMORY,
                }
            )

    return containers


def list_containers_with_memory_status():
    containers = []
    if not os.path.isdir(DIMENSION_DIR):
        return containers

    for filename in os.listdir(DIMENSION_DIR):
        if filename.endswith(".dc.json"):
            container_id = filename.replace(".dc.json", "")
            containers.append({"id": container_id, "in_memory": container_id in CONTAINER_MEMORY})
    return containers


# -------------------------------------------------------------------------
# Microgrid injection helpers
# -------------------------------------------------------------------------
def _coord_key(coord: Tuple[int, int, int]) -> str:
    x, y, z = coord
    return f"{int(x)},{int(y)},{int(z)}"


def inject_glyphs_into_universal_container_system(
    container_id: str,
    glyphs: List[Dict[str, Any]],
    placement: Optional[List[Tuple[int, int, int]]] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    container = load_dc_container(container_id)
    microgrid = container.setdefault("microgrid", {})  # "x,y,z" -> meta

    if placement:
        if len(placement) != len(glyphs):
            raise ValueError("placement length must match glyphs length")
        for g, coord in zip(glyphs, placement):
            key = _coord_key(coord)
            if not overwrite and key in microgrid:
                continue
            microgrid[key] = g
    else:
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


def carve_glyph_cube(container_path: str, coord: str, glyph: str, meta: Optional[dict] = None):
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
        json.dump(data, f, indent=2, ensure_ascii=False)

    MEMORY.store(
        {
            "role": "system",
            "label": "glyph_carved",
            "content": f"Carved glyph '{glyph}' into {container_path} at {coord}",
            "metadata": {"coord": coord, "glyph": glyph, **(meta or {})},
        }
    )

    print(f"[🪓] Glyph '{glyph}' carved at {coord} in {os.path.basename(container_path)}")


def inject_glyphs_into_container(
    container_filename: str, glyphs: List[dict], source: str = "manual"
) -> bool:
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
            for _key, cube in (container.get("cubes") or {}).items():
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
            json.dump(container, f, indent=2, ensure_ascii=False)

        print(f"[✅] Injected {inserted} glyph(s) into {container_filename}")
        return inserted > 0

    except Exception as e:
        print(f"[❌] Error injecting glyphs into container: {e}")
        return False
