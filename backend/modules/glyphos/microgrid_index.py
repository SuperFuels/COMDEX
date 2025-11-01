# File: backend/modules/glyphos/microgrid_index.py

from typing import Dict, Tuple, Optional, List
import time

class MicrogridIndex:
    def __init__(self):
        # Maps (x, y, z, optional layer) -> glyph metadata dict
        self.glyph_map: Dict[Tuple[int, int, int, Optional[int]], Dict] = {}

    def register_glyph(
        self,
        x: int,
        y: int,
        z: int,
        glyph: str,
        layer: Optional[int] = None,
        metadata: Optional[Dict] = None
    ):
        coord = (x, y, z, layer)
        meta = metadata.copy() if metadata else {}
        meta.update({
            "glyph": glyph,
            "timestamp": time.time(),
            "activations": 0,
            "energy": meta.get("energy", 1.0)
        })
        self.glyph_map[coord] = meta
        print(f"📍 Registered glyph '{glyph}' at {coord} with metadata {meta}")

    def get_glyph(
        self,
        x: int,
        y: int,
        z: int,
        layer: Optional[int] = None
    ) -> Optional[Dict]:
        return self.glyph_map.get((x, y, z, layer))

    def activate_glyph(
        self,
        x: int,
        y: int,
        z: int,
        layer: Optional[int] = None
    ):
        coord = (x, y, z, layer)
        glyph_data = self.glyph_map.get(coord)
        if glyph_data:
            glyph_data["activations"] += 1
            glyph_data["energy"] *= 0.98  # symbolic decay logic
            glyph_data["timestamp"] = time.time()
            print(f"⚡ Activated glyph at {coord} -> {glyph_data}")

    def sweep_region(
        self,
        x_range: range,
        y_range: range,
        z_range: range,
        layer: Optional[int] = None
    ) -> Dict[Tuple[int, int, int, Optional[int]], Dict]:
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
        """Export internal glyph map as a string-keyed dict."""
        return {
            f"{x},{y},{z},{layer if layer is not None else 'null'}": meta
            for (x, y, z, layer), meta in self.glyph_map.items()
        }

    def import_index(self, data: Dict[str, Dict]):
        """Import string-keyed glyph map into internal structure."""
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

    def query_by_type(
        self,
        glyph_type: str,
        layer_filter: Optional[int] = None
    ) -> Dict[Tuple[int, int, int, Optional[int]], Dict]:
        """Return all glyphs of a given type, optionally filtered by layer."""
        return {
            coord: meta
            for coord, meta in self.glyph_map.items()
            if meta.get("type") == glyph_type and (layer_filter is None or coord[3] == layer_filter)
        }

    def get_glyph_type_map(self) -> Dict[str, List[str]]:
        """Return a glyph-type mapping for frontend HUD overlays."""
        type_map: Dict[str, List[str]] = {}
        for (x, y, z, layer), meta in self.glyph_map.items():
            gtype = meta.get("type", "unknown")
            key = f"{x},{y},{z},{layer if layer is not None else 'null'}"
            type_map.setdefault(gtype, []).append(key)
        return type_map

    def simulate_decay(self, decay_rate: float = 0.99, threshold: float = 0.01):
        """Globally decays energy values for all glyphs."""
        decayed = 0
        for coord, meta in self.glyph_map.items():
            original = meta["energy"]
            meta["energy"] *= decay_rate
            if meta["energy"] < threshold:
                meta["energy"] = 0.0
            if original != meta["energy"]:
                decayed += 1
        print(f"🕒 Simulated decay for {decayed} glyphs at rate {decay_rate}")

def cube_to_coord(cube: dict) -> str:
    """Convert a cube dictionary to a coordinate string."""
    x = cube.get("x", "?")
    y = cube.get("y", "?")
    z = cube.get("z", "?")
    t = cube.get("t", "?")
    return f"{x},{y},{z},{t}"