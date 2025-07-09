# backend/modules/glyphos/microgrid_index.py

from typing import Dict, Tuple, Optional
import time

class MicrogridIndex:
    def __init__(self):
        # Maps: (x, y, z, [optional layer]) → glyph metadata
        self.glyph_map: Dict[Tuple[int, int, int, Optional[int]], Dict] = {}

    def register_glyph(self, x: int, y: int, z: int, glyph: str, layer: Optional[int] = None, metadata: Optional[Dict] = None):
        coord = (x, y, z, layer)
        meta = metadata or {}
        meta.update({
            "glyph": glyph,
            "timestamp": time.time(),
            "activations": 0,
            "energy": meta.get("energy", 1.0)
        })
        self.glyph_map[coord] = meta
        print(f"📍 Registered glyph '{glyph}' at {coord} with metadata {meta}")

    def get_glyph(self, x: int, y: int, z: int, layer: Optional[int] = None) -> Optional[Dict]:
        return self.glyph_map.get((x, y, z, layer))

    def activate_glyph(self, x: int, y: int, z: int, layer: Optional[int] = None):
        coord = (x, y, z, layer)
        if coord in self.glyph_map:
            self.glyph_map[coord]["activations"] += 1
            self.glyph_map[coord]["energy"] *= 0.98  # small decay
            print(f"⚡ Activated glyph at {coord} → {self.glyph_map[coord]}")

    def sweep_region(self, x_range: range, y_range: range, z_range: range, layer: Optional[int] = None) -> Dict[Tuple[int, int, int, Optional[int]], Dict]:
        results = {}
        for x in x_range:
            for y in y_range:
                for z in z_range:
                    coord = (x, y, z, layer)
                    if coord in self.glyph_map:
                        results[coord] = self.glyph_map[coord]
        print(f"🔍 Swept region and found {len(results)} active glyphs")
        return results

    def export_index(self) -> Dict[str, Dict]:
        return {
            f"{x},{y},{z},{layer if layer is not None else 'null'}": meta
            for (x, y, z, layer), meta in self.glyph_map.items()
        }

    def import_index(self, data: Dict[str, Dict]):
        self.glyph_map.clear()
        for key, meta in data.items():
            parts = key.split(",")
            if len(parts) < 3:
                print(f"⚠️ Skipping malformed glyph key: '{key}'")
                continue
            try:
                x, y, z = map(int, parts[:3])
                layer = int(parts[3]) if len(parts) == 4 and parts[3] != "null" else None
                self.glyph_map[(x, y, z, layer)] = meta
            except Exception as e:
                print(f"❌ Error importing glyph at key '{key}': {e}")
        print(f"📦 Imported {len(self.glyph_map)} glyphs into microgrid index")

    def query_by_type(self, glyph_type: str) -> Dict[Tuple[int, int, int, Optional[int]], Dict]:
        return {
            coord: meta for coord, meta in self.glyph_map.items()
            if meta.get("type") == glyph_type
        }

def cube_to_coord(cube: dict) -> str:
    """Convert a cube dictionary to a coordinate string."""
    x = cube.get("x", "?")
    y = cube.get("y", "?")
    z = cube.get("z", "?")
    t = cube.get("t", "?")
    return f"{x},{y},{z},{t}"