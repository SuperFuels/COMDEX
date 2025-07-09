# File: backend/modules/glyphos/glyph_reverse_loader.py

import os
import json
from typing import Dict, Any, List

from backend.modules.dna_chain.dc_handler import load_dimension
from backend.modules.glyphos.glyph_parser import GlyphParser
from backend.modules.glyphos.microgrid_index import MicrogridIndex

# Neuroglyph pattern markers
GLYPH_CHAIN_SYMBOLS = {"🧠", "✧", "🪄", "🧬", "📐"}


def cube_to_coord(cube: Dict[str, Any]) -> str:
    """Convert cube's x/y/z into a coordinate string."""
    x = cube.get("x", 0)
    y = cube.get("y", 0)
    z = cube.get("z", 0)
    return f"{x},{y},{z}"


def parse_glyph(bytecode: str) -> Dict[str, Any]:
    """Use GlyphParser to interpret a single bytecode string."""
    parser = GlyphParser()
    return parser.parse(bytecode)


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


def extract_glyph_chain(microgrid: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Reconstruct a chain of symbolic glyphs from a microgrid.
    Looks for sequential or clustered logic patterns like 🧠 → ✧ → 🪄
    """
    chain = []
    for coord, cube in microgrid.items():
        glyph = cube.get("glyph")
        if glyph in GLYPH_CHAIN_SYMBOLS:
            chain.append({
                "coord": coord,
                "glyph": glyph,
                "type": cube.get("type"),
                "tag": cube.get("tag"),
                "value": cube.get("value"),
                "action": cube.get("action")
            })
    # Optional: sort by spatial coordinates for consistency
    chain.sort(key=lambda c: tuple(map(int, c["coord"].split(","))))
    return chain


def unfold_logic_tree(microgrid: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts the extracted glyph chain into a symbolic tree (branch model).
    """
    chain = extract_glyph_chain(microgrid)
    if not chain:
        return {"tree": [], "summary": "No glyph chain found."}

    root = {"node": chain[0], "children": []}
    current = root

    for next_node in chain[1:]:
        current["children"] = [{"node": next_node, "children": []}]
        current = current["children"][0]

    return {"tree": root, "summary": f"Loaded {len(chain)} glyph nodes."}


if __name__ == "__main__":
    # Example CLI usage
    import sys
    if len(sys.argv) < 2:
        print("Usage: python glyph_reverse_loader.py path/to/container.dc")
    else:
        path = sys.argv[1]
        results = extract_glyphs_from_container(path)
        print(json.dumps(results, indent=2))