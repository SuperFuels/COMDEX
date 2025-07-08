# glyph_sweeper.py

from backend.modules.glyphos.microgrid_index import MicrogridIndex

class GlyphSweeper:
    def __init__(self, index: MicrogridIndex):
        self.index = index

    def find_linear_patterns(self):
        patterns = []
        checked = set()

        for (x, y, z), glyph in self.index.glyph_map.items():
            if (x, y, z) in checked:
                continue

            # Check line in x-axis
            line = [(x + i, y, z) for i in range(3)]
            if all(self.index.get_glyph(*pos) for pos in line):
                patterns.append(("line_x", line))
                checked.update(line)

            # Check line in y-axis
            line = [(x, y + i, z) for i in range(3)]
            if all(self.index.get_glyph(*pos) for pos in line):
                patterns.append(("line_y", line))
                checked.update(line)

            # Check line in z-axis
            line = [(x, y, z + i) for i in range(3)]
            if all(self.index.get_glyph(*pos) for pos in line):
                patterns.append(("line_z", line))
                checked.update(line)

        print(f"🔍 Found {len(patterns)} glyph pattern(s)")
        return patterns

    def detect_glyph_clusters(self):
        from collections import defaultdict
        freq = defaultdict(int)

        for _, glyph in self.index.glyph_map.items():
            freq[glyph] += 1

        print(f"📊 Glyph distribution: {dict(freq)}")
        return dict(freq)