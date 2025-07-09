# backend/modules/glyphos/glyph_reverse_loader.py

import os
import json
from backend.modules.dna_chain.dc_handler import load_dimension
from backend.modules.glyphos.glyph_parser import GlyphParser
from backend.modules.glyphos.microgrid_index import MicrogridIndex


def extract_glyphs_from_container(dc_path: str):
    """Extract glyph-like bytecode from all cubes in a .dc container."""
    dimension = load_dimension(dc_path)
    glyphs = []

    for cube in dimension.get("cubes", []):
        bytecode = cube.get("bytecode")
        coord = cube_to_coord(cube)
        if bytecode:
            try:
                glyph = parse_glyph(bytecode)
                glyphs.append({**glyph, "coord": coord})
            except Exception as e:
                print(f"[⚠️] Failed to parse bytecode at {coord}: {e}")

    return glyphs


if __name__ == "__main__":
    # Example CLI usage
    import sys
    if len(sys.argv) < 2:
        print("Usage: python glyph_reverse_loader.py path/to/container.dc")
    else:
        path = sys.argv[1]
        results = extract_glyphs_from_container(path)
        print(json.dumps(results, indent=2))