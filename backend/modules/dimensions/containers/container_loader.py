"""
📥 UCS Container Loader
-----------------------------------------------------
Handles loading and instantiation of all container types (Hoberman, Symbolic Expansion, UCSBase, etc.)
Integrates with:
    * UCSBaseContainer for shared features (micro-grid, time dilation, gravity)
    * HobermanContainer + SymbolicExpansionContainer (legacy compatibility)
    * ucs_runtime + geometry templates (.dc.json)
    * sqi_container_registry for KG-aware symbolic registration
"""

import json
import os
from typing import Dict, Any, Union

from backend.modules.dimensions.containers.hoberman_container import HobermanContainer
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer
from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCS_TEMPLATE_DIR
from backend.modules.dna_chain.dc_handler import load_dimension
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime


# ✅ Symbolic Container Registration Hook
from backend.modules.sqi.sqi_container_registry import _registry_register

# ✅ UCS Utils - normalize input
from backend.modules.dimensions.universal_container_system.ucs_utils import normalize_container_dict

SQI_NS = "ucs://knowledge"


def load_container_from_json(container_json: Dict[str, Any]) -> Union[UCSBaseContainer, HobermanContainer, SymbolicExpansionContainer, Dict[str, Any]]:
    """
    Auto-detect and load containers:
        - Hoberman (legacy)
        - Symbolic Expansion (legacy)
        - UCSBaseContainer (new standard)
    """
    # ✅ Normalize input first (even if passed from elsewhere)
    container_json = normalize_container_dict(container_json)

    container_type = container_json.get("container_type", "ucs_base")
    runtime_mode = container_json.get("runtime_mode", "expanded")
    container_id = container_json.get("id") or container_json.get("container_id")
    name = container_json.get("name", f"Container-{container_id or 'anon'}")

    # ✅ UCS Base Container (New Standard)
    if container_type == "ucs_base":
        geometry = container_json.get("geometry_type", "tesseract")
        container = UCSBaseContainer(
            name=name,
            geometry=geometry,
            runtime=get_ucs_runtime()
        )
        container.id = container_id or "anon"
        container.init_micro_grid()
        container.apply_time_dilation(container_json.get("properties", {}).get("time_factor", 1.0))

        if runtime_mode == "expanded":
            container.execute()

        if container.id:
            _registry_register(container.id, SQI_NS)

        return container

    # ✅ Hoberman (Legacy)
    if container_type == "hoberman":
        glyphs = container_json.get("hoberman_seed", {}).get("glyphs", [])
        hob = HobermanContainer(container_id=container_id)
        hob.id = container_id or "anon"
        hob.from_glyphs(glyphs)

        if runtime_mode == "expanded":
            hob.inflate()

        if hob.id:
            _registry_register(hob.id, SQI_NS)

        return hob

    # ✅ Symbolic Expansion (Legacy)
    if container_type == "symbolic_expansion":
        glyphs = container_json.get("hoberman_seed", {}).get("glyphs", [])
        sec = SymbolicExpansionContainer(container_id=container_id)
        sec.id = container_id or "anon"
        sec.load_seed(glyphs)

        if runtime_mode == "expanded":
            sec.expand()

        if sec.id:
            _registry_register(sec.id, SQI_NS)

        return sec

    # ❌ Fallback (raw JSON) - register if ID exists
    fallback_id = container_json.get("id")
    if fallback_id:
        _registry_register(fallback_id, SQI_NS)

    return container_json

def register_container(container_id: str, container_path: str) -> dict:
    from backend.modules.runtime.container_runtime import ContainerRuntime
    """
    Load a .dc.json container and register it into the UCS runtime and KG registry.

    Args:
        container_id: ID of the container to register
        container_path: Path to the .dc.json file

    Returns:
        The loaded container object
    """
    if not os.path.exists(container_path):
        raise FileNotFoundError(f"Container file not found: {container_path}")

    with open(container_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    container = load_container_from_json(raw_data)

    # Manually set ID if needed
    if hasattr(container, "id") and not container.id:
        container.id = container_id

    # Register into runtime if applicable
    if isinstance(container, (UCSBaseContainer, HobermanContainer, SymbolicExpansionContainer)):
        ContainerRuntime.register(container)

    # Always register with SQI registry
    _registry_register(container_id, SQI_NS)

    return container

def load_container_from_file(file_path: str):
    """
    Load container definition from a .dc.json file and instantiate.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Container file not found: {file_path}")

    with open(file_path, "r") as f:
        container_json = json.load(f)

    return load_container_from_json(container_json)


def auto_load_all_templates():
    """
    Auto-load and instantiate all containers from the UCS templates directory.
    Useful for bootstrapping the full container ecosystem (e.g., Tesseract -> Quantum -> Vortex -> Black Hole -> Torus).
    """
    containers = {}

    if not os.path.exists(UCS_TEMPLATE_DIR):
        print(f"⚠️ UCS templates folder not found: {UCS_TEMPLATE_DIR}")
        return containers

    for file in os.listdir(UCS_TEMPLATE_DIR):
        if file.endswith(".dc.json"):
            path = os.path.join(UCS_TEMPLATE_DIR, file)
            try:
                container = load_container_from_file(path)
                containers[getattr(container, "name", file)] = container
            except Exception as e:
                print(f"❌ Failed to load container '{file}': {e}")

    return containers


def load_decrypted_container(container_id: str) -> dict:
    from backend.modules.runtime.container_runtime import ContainerRuntime
    """
    Securely load a decrypted container using the active runtime instance.
    """
    state_manager = StateManager()
    runtime = ContainerRuntime(state_manager)

    container = load_dimension(container_id)
    state_manager.set_current_container(container)

    return runtime.get_decrypted_current_container()


def load_container_by_id(container_id: str) -> dict:
    """
    Load a UCS container by its ID using the UCS runtime system.
    Includes debug path inspection and optional fallback.
    """
    from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
    from backend.modules.sqi.sqi_container_registry import _registry_register, SQI_NS

    ucs = get_ucs_runtime()

    # Debug log: show available container IDs
    available_ids = list(ucs.container_registry.keys())
    print(f"[📦] Available containers in UCS: {available_ids}")

    container = ucs.load_container(container_id)

    if not container:
        raise ValueError(
            f"❌ Container '{container_id}' not found in UCS runtime.\n"
            f"Available: {available_ids}"
        )

    if hasattr(container, "id") and container.id:
        _registry_register(container.id, SQI_NS)

    return container

__all__ = [
    "load_container_from_json",
    "load_container_from_file",
    "auto_load_all_templates",
    "load_decrypted_container",
    "load_container_by_id",
    "register_container",
]