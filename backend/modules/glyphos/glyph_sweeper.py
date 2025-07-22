# glyph_sweeper.py

from backend.modules.glyphos.microgrid_index import MicrogridIndex
from collections import defaultdict
from typing import List, Tuple, Dict


class GlyphSweeper:
    def __init__(self, index: MicrogridIndex):
        self.index = index

    def find_linear_patterns(self) -> List[Tuple[str, List[Tuple[int, int, int]]]]:
        """Detects straight 3-glyph lines in X, Y, Z directions and diagonals."""
        patterns = []
        checked = set()

        directions = {
            "line_x": (1, 0, 0),
            "line_y": (0, 1, 0),
            "line_z": (0, 0, 1),
            "diag_xy": (1, 1, 0),
            "diag_xz": (1, 0, 1),
            "diag_yz": (0, 1, 1),
            "diag_xyz": (1, 1, 1)
        }

        for (x, y, z), _ in self.index.glyph_map.items():
            for name, (dx, dy, dz) in directions.items():
                line = [(x + i * dx, y + i * dy, z + i * dz) for i in range(3)]
                if all(self.index.get_glyph(*pos) for pos in line) and not any(p in checked for p in line):
                    patterns.append((name, line))
                    checked.update(line)

        print(f"🔍 Found {len(patterns)} glyph line/diagonal pattern(s)")
        return patterns

    def detect_glyph_clusters(self) -> Dict[str, int]:
        """Counts frequency of each glyph symbol and groups by symbolic type."""
        freq = defaultdict(int)
        for _, glyph in self.index.glyph_map.items():
            if isinstance(glyph, str):
                freq[glyph] += 1
            elif isinstance(glyph, dict) and "glyph" in glyph:
                freq[glyph["glyph"]] += 1

        print(f"📊 Glyph distribution: {dict(freq)}")
        return dict(freq)

    def find_3x3_blocks(self) -> List[Tuple[str, List[Tuple[int, int, int]]]]:
        """Detects solid 3x3x3 glyph blocks (cubes)."""
        found = []
        checked = set()

        for (x, y, z), _ in self.index.glyph_map.items():
            cube = [
                (x + dx, y + dy, z + dz)
                for dx in range(3)
                for dy in range(3)
                for dz in range(3)
            ]
            if all(self.index.get_glyph(*pos) for pos in cube) and not any(p in checked for p in cube):
                found.append(("cube_3x3x3", cube))
                checked.update(cube)

        print(f"🧊 Found {len(found)} 3D glyph cube(s)")
        return found

    def extract_scroll_fragments(self) -> List[dict]:
        """Generates symbolic scroll fragments from detected patterns."""
        scrolls = []
        lines = self.find_linear_patterns()
        cubes = self.find_3x3_blocks()

        for tag, positions in lines + cubes:
            fragment = {
                "type": "scroll_fragment",
                "tag": tag,
                "glyphs": [
                    {
                        "coords": pos,
                        "glyph": self.index.get_glyph(*pos)
                    }
                    for pos in positions
                ]
            }
            scrolls.append(fragment)

        print(f"📜 Generated {len(scrolls)} scroll fragments")
        return scrolls

    def analyze(self) -> dict:
        """Run full sweep and return all findings in one package."""
        return {
            "patterns": self.find_linear_patterns(),
            "cubes": self.find_3x3_blocks(),
            "clusters": self.detect_glyph_clusters(),
            "scroll_fragments": self.extract_scroll_fragments()
        }