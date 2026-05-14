# Dimension ↔ Tessaris Runtime Loop
# Scans 4D cube field and routes glyphs to symbolic thought

from backend.modules.dimensions.dimension_kernel import DimensionKernel
from backend.modules.tessaris.tessaris_engine import TessarisEngine

class DimensionThoughtRunner:
    def __init__(self, container_id="default"):
        self.kernel = DimensionKernel(container_id)
        self.tessaris = TessarisEngine(container_id)
        self.last_tick = 0

    def tick_once(self):
        tick_data = self.kernel.tick()
        current_tick = tick_data["tick"]
        glyph_events = tick_data.get("glyph_actions", [])

        print(f"\n[⏳] Tick {current_tick} | Active Cubes: {tick_data['active_cubes']} | Glyph Events: {len(glyph_events)}")

        for event in glyph_events:
            location = event.get("location")
            glyphs = self.kernel.get_glyph_at(*location)
            if glyphs:
                cube_data = {
                    "position": {
                        "x": location[0],
                        "y": location[1],
                        "z": location[2],
                        "t": location[3],
                    },
                    "glyphs": glyphs
                }
                self.tessaris.process_triggered_cube(cube_data, source=f"cube@{location}")

        self.last_tick = current_tick
        return {
            "tick": current_tick,
            "glyphs_processed": len(glyph_events)
        }

    def run_for_ticks(self, count=5):
        results = []
        for _ in range(count):
            result = self.tick_once()
            results.append(result)
        return results

    def inject_glyph(self, x, y, z, t, glyph):
        return self.kernel.place_glyph(x, y, z, t, glyph)

    def expand_space(self, axis="z", amount=1):
        return self.kernel.expand(axis, amount)

    def snapshot(self):
        return self.kernel.dump_snapshot()