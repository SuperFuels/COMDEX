"""
📥 UCS Container Loader
-----------------------------------------------------
Handles loading and instantiation of all container types (Hoberman, Symbolic Expansion, UCSBase, etc.)
Integrates with:
    • UCSBaseContainer for shared features (micro-grid, time dilation, gravity)
    • HobermanContainer + SymbolicExpansionContainer (legacy compatibility)
    • ucs_runtime + geometry templates (.dc.json)
"""

import json
import os
from typing import Dict, Any, Union

from backend.modules.dimensions.universal_container_system.hoberman import HobermanContainer
from backend.modules.dimensions.universal_container_system.symbolic_expansion import SymbolicExpansionContainer
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.dimensions.universal_container_system.ucs_geometry_loader import UCS_TEMPLATE_DIR


def load_container_from_json(container_json: Dict[str, Any]) -> Union[UCSBaseContainer, HobermanContainer, SymbolicExpansionContainer, Dict[str, Any]]:
    """
    Auto-detect and load containers:
        - Hoberman (legacy)
        - Symbolic Expansion (legacy)
        - UCSBaseContainer (new standard)
    """

    container_type = container_json.get("container_type", "ucs_base")
    runtime_mode = container_json.get("runtime_mode", "expanded")
    container_id = container_json.get("id") or container_json.get("container_id")
    name = container_json.get("name", f"Container-{container_id or 'anon'}")

    # ✅ UCS Base Container (New)
    if container_type == "ucs_base":
        geometry = container_json.get("geometry_type", "tesseract")
        container = UCSBaseContainer(name=name, geometry=geometry, runtime=ucs_runtime)
        container.init_micro_grid()
        container.apply_time_dilation(container_json.get("properties", {}).get("time_factor", 1.0))
        if runtime_mode == "expanded":
            container.execute()
        return container

    # ✅ Hoberman (Legacy)
    if container_type == "hoberman":
        glyphs = container_json.get("hoberman_seed", {}).get("glyphs", [])
        hob = HobermanContainer(container_id=container_id)
        hob.from_glyphs(glyphs)
        if runtime_mode == "expanded":
            hob.inflate()
        return hob

    # ✅ Symbolic Expansion (Legacy)
    if container_type == "symbolic_expansion":
        glyphs = container_json.get("hoberman_seed", {}).get("glyphs", [])
        sec = SymbolicExpansionContainer(container_id=container_id)
        sec.load_seed(glyphs)
        if runtime_mode == "expanded":
            sec.expand()
        return sec

    # Fallback (raw JSON)
    return container_json


def load_container_from_file(file_path: str):
    """Load container definition from a .dc.json file and instantiate."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Container file not found: {file_path}")
    with open(file_path, "r") as f:
        container_json = json.load(f)
    return load_container_from_json(container_json)


def auto_load_all_templates():
    """
    Auto-load and instantiate all containers from the UCS templates directory.
    Useful for bootstrapping the full container ecosystem (e.g., Tesseract → Quantum → Vortex → Black Hole → Torus).
    """
    containers = {}
    if not os.path.exists(UCS_TEMPLATE_DIR):
        print(f"⚠️ UCS templates folder not found: {UCS_TEMPLATE_DIR}")
        return containers

    for file in os.listdir(UCS_TEMPLATE_DIR):
        if file.endswith(".dc.json"):
            path = os.path.join(UCS_TEMPLATE_DIR, file)
            container = load_container_from_file(path)
            containers[container.name if hasattr(container, "name") else file] = container
    return containers


__all__ = [
    "load_container_from_json",
    "load_container_from_file",
    "auto_load_all_templates",
]