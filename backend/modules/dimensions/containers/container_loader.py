import json
from typing import Dict, Any
from backend.modules.containers.hoberman_container import HobermanContainer
from backend.modules.containers.symbolic_expansion_container import SymbolicExpansionContainer

def load_container_from_json(container_json: Dict[str, Any]):
    """Auto-detect and load special container formats like Hoberman or Symbolic Expansion."""
    container_type = container_json.get("container_type", "standard")
    runtime_mode = container_json.get("runtime_mode", "expanded")
    container_id = container_json.get("id")

    if container_type == "hoberman":
        glyphs = container_json.get("hoberman_seed", {}).get("glyphs", [])
        container = HobermanContainer(container_id=container_id)
        container.from_glyphs(glyphs)
        if runtime_mode == "expanded":
            container.inflate()
        return container

    elif container_type == "symbolic_expansion":
        glyphs = container_json.get("hoberman_seed", {}).get("glyphs", [])
        sec = SymbolicExpansionContainer(container_id=container_id)
        sec.load_seed(glyphs)
        if runtime_mode == "expanded":
            sec.expand()
        return sec

    # Fallback to standard logic
    return container_json  # Will be parsed by default runtime