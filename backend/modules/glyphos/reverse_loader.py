# backend/modules/glyphos/reverse_loader.py

import json
import os
from typing import List, Dict

from backend.modules.glyphos.glyph_parser import parse_glyph_line


def extract_glyphs_from_cube(cube_data: Dict) -> List[Dict]:
    """
    Reverse-load glyphs from a .dc container cube.
    Looks for 'glyph_lines' or raw bytecode and parses them.
    """
    glyphs = []
    raw_lines = cube_data.get("glyph_lines") or cube_data.get("bytecode")
    if not raw_lines:
        return []

    for line in raw_lines:
        try:
            glyph = parse_glyph_line(line)
            if glyph:
                glyphs.append(glyph)
        except Exception as e:
            print(f"[⚠️] Failed to parse glyph line: {line} - {e}")
            continue

    return glyphs


def reverse_load_all_cubes(dc_path: str) -> Dict[str, List[Dict]]:
    """
    Load all .dc cubes from a given file and extract glyphs from each.
    Returns mapping: coord -> [glyphs]
    """
    if not os.path.exists(dc_path):
        raise FileNotFoundError(f".dc file not found at: {dc_path}")

    with open(dc_path, "r") as f:
        dc_data = json.load(f)

    extracted = {}
    for coord, cube in dc_data.items():
        glyphs = extract_glyphs_from_cube(cube)
        if glyphs:
            extracted[coord] = glyphs

    return extracted