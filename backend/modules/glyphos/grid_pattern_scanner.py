# File: backend/modules/glyphos/grid_pattern_scanner.py

from collections import defaultdict
from typing import List, Dict, Tuple, TypedDict, Optional

# Define common logic glyphs in the activation chain
DEFAULT_GLYPH_CHAIN = ["🧠", "✧", "🪄"]  # 🧠 → ✧ → 🪄

# Valid 3D neighbor offsets (6 directions: N/S/E/W/Up/Down)
NEIGHBOR_OFFSETS = [
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1)
]

class PatternMatch(TypedDict):
    pattern: List[str]
    path: List[str]

def parse_coord(coord_str: str) -> Tuple[int, int, int]:
    return tuple(map(int, coord_str.split(",")))

def coord_to_str(coord: Tuple[int, int, int]) -> str:
    return f"{coord[0]},{coord[1]},{coord[2]}"

def scan_microgrid_for_patterns(
    container: Dict,
    glyph_chain: Optional[List[str]] = None
) -> List[PatternMatch]:
    """
    Scans the microgrid of a container for recognizable logic chains (e.g. 🧠→✧→🪄).
    
    Args:
        container (Dict): The container JSON with a 'microgrid' key.
        glyph_chain (List[str], optional): Ordered glyphs to detect in a linked path.

    Returns:
        List[PatternMatch]: List of detected chains with path and glyph sequence.
    """
    microgrid = container.get("microgrid", {})
    if not microgrid:
        return []

    chain_template = glyph_chain or DEFAULT_GLYPH_CHAIN
    visited = set()
    chains: List[PatternMatch] = []

    glyph_map = {
        parse_coord(coord): data
        for coord, data in microgrid.items()
        if data.get("glyph") in chain_template
    }

    for coord, data in glyph_map.items():
        if coord in visited or data.get("glyph") != chain_template[0]:
            continue

        chain = [(coord, data["glyph"])]
        visited.add(coord)
        current = coord

        for next_glyph in chain_template[1:]:
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
                break

        if len(chain) == len(chain_template):
            chains.append({
                "pattern": [g for _, g in chain],
                "path": [coord_to_str(c) for c, _ in chain]
            })

    # Optional debugging
    if chains:
        print(f"🔗 Detected {len(chains)} logic chain(s):")
        for c in chains:
            print(f" - Path: {c['path']} Pattern: {c['pattern']}")

    return sorted(chains, key=lambda c: c["path"])