# File: backend/modules/dna_chain/trigger_engine.py

from backend.modules.dna_chain.dc_handler import load_dc_container
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.aion_reflection.reflection_engine import ReflectionEngine
from backend.modules.consciousness.state_manager import StateManager


def _get_container(container_id: str) -> dict:
    """
    Prefer the in-memory UCS runtime container; fall back to on-disk loader.
    """
    c = ucs_runtime.get_container(container_id)
    if c and (c.get("microgrid") or c.get("cubes") or c.get("glyph_grid")):
        return c
    return load_dc_container(container_id)


def _extract_microgrid(container: dict) -> dict:
    """
    Normalize different container layouts into a dict-like microgrid:
    - 'microgrid' already dict of coord -> meta
    - 'cubes' as dict of coord -> meta
    - 'glyph_grid' (list or nested) -> flatten into { "x,y,z": {"glyph": ...} }
    """
    if isinstance(container.get("microgrid"), dict):
        return container["microgrid"]

    if isinstance(container.get("cubes"), dict):
        return container["cubes"]

    # Fallback: try to flatten glyph_grid (list-based) into coord->meta
    grid = container.get("glyph_grid")
    if grid and isinstance(grid, list):
        norm = {}
        for x, layer in enumerate(grid):
            if not isinstance(layer, list): 
                continue
            for y, row in enumerate(layer):
                if not isinstance(row, list): 
                    continue
                for z, cell in enumerate(row):
                    if not cell:
                        continue
                    # cell could be a glyph string or a dict already
                    if isinstance(cell, dict):
                        meta = dict(cell)
                    else:
                        meta = {"glyph": cell}
                    norm[f"{x},{y},{z}"] = meta
        return norm

    return {}


def check_glyph_triggers(container_id: str):
    """
    Scan a loaded .dc container and execute any known triggers based on glyph + tag.
    """
    container = _get_container(container_id)
    microgrid = _extract_microgrid(container)

    for coord, meta in microgrid.items():
        glyph = meta.get("glyph")
        tag = meta.get("tag")

        if glyph == "✦" and tag == "dream_trigger":
            print(f"[⚡] Dream trigger found at {coord}, launching dream cycle...")
            ReflectionEngine().reflect()

        elif glyph == "🧭" and tag == "teleport":
            destination = meta.get("destination")
            if destination:
                print(f"[⚡] Teleport trigger found at {coord}, going to {destination}...")
                StateManager().teleport_to(destination)

        elif glyph == "🧠" and tag == "reflect":
            print(f"[⚡] Reflection glyph found at {coord}, triggering reflection...")
            ReflectionEngine().reflect()

        # Add more glyph+tag behaviors here as needed

    print("[✅] Trigger scan complete.")