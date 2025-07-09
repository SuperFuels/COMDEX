import json
from backend.modules.dna_chain.dc_handler import load_dimension, save_dimension
from backend.modules.hexcore.memory_engine import MEMORY

def mutate_glyph(container, x, y, new_glyph):
    """Replace a glyph at given coordinates and return updated container."""
    cube = container["grid"][y][x]
    old_glyph = cube.get("glyph", None)
    cube["glyph"] = new_glyph
    print(f"🔁 Mutated glyph at ({x},{y}): {old_glyph} → {new_glyph}")
    return container

def run():
    path = "backend/modules/dimensions/containers/test_grid.dc.json"
    container = load_dimension(path)
    
    mutated = mutate_glyph(container, x=1, y=1, new_glyph="reflect:light")
    MEMORY.store_memory({
        "type": "mutation",
        "role": "system",
        "content": f"Mutated glyph at (1,1) to 'reflect:light'",
        "container_id": container.get("id", "unknown")
    })

    save_dimension(mutated, path)
    print("✅ Container updated and saved.")

if __name__ == "__main__":
    run()
