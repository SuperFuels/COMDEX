# File: backend/modules/glyphos/grid_pattern_scanner.py

from collections import defaultdict
from typing import List, Dict, Tuple

# Define common logic glyphs in the activation chain
GLYPH_CHAIN = ["🧠", "✧", "🪄"]  # 🧠 → ✧ → 🪄

# Valid 3D neighbor offsets (6 directions: N/S/E/W/Up/Down)
NEIGHBOR_OFFSETS = [
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1)
]

def parse_coord(coord_str: str) -> Tuple[int, int, int]:
    return tuple(map(int, coord_str.split(",")))

def coord_to_str(coord: Tuple[int, int, int]) -> str:
    return f"{coord[0]},{coord[1]},{coord[2]}"

def scan_microgrid_for_patterns(container: Dict) -> List[Dict]:
    """
    Scans the microgrid of a container for recognizable logic patterns like 🧠→✧→🪄.
    Returns a list of detected chains with coordinates and glyphs.
    """
    microgrid = container.get("microgrid", {})
    if not microgrid:
        return []

    visited = set()
    chains = []

    # Build fast lookup
    glyph_map = {parse_coord(coord): data for coord, data in microgrid.items() if data.get("glyph") in GLYPH_CHAIN}

    for coord, data in glyph_map.items():
        if coord in visited:
            continue

        # Try to walk the chain from this starting point
        glyph = data.get("glyph")
        if glyph != GLYPH_CHAIN[0]:
            continue  # Only begin from 🧠

        chain = [(coord, glyph)]
        visited.add(coord)

        current = coord
        for next_glyph in GLYPH_CHAIN[1:]:
            found = False
            for dx, dy, dz in NEIGHBOR_OFFSETS:
                neighbor = (current[0] + dx, current[1] + dy, current[2] + dz)
                if neighbor in visited:
                    continue
                neighbor_data = glyph_map.get(neighbor)
                if neighbor_data and neighbor_data.get("glyph") == next_glyph:
                    chain.append((neighbor, next_glyph))
                    visited.add(neighbor)
                    current = neighbor
                    found = True
                    break
            if not found:
                break  # Abort chain if next glyph not found

        if len(chain) == len(GLYPH_CHAIN):
            chains.append({
                "pattern": [g for _, g in chain],
                "path": [coord_to_str(c) for c, _ in chain]
            })

    return chains
