# backend/modules/glyphos/runtime_loop.py

import time
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.glyphos.glyph_executor import GlyphExecutor


class GlyphRuntimeLoop:
    def __init__(self):
        self.state_manager = StateManager()
        self.executor = GlyphExecutor(self.state_manager)
        self.seen_glyphs = set()

    def tick(self):
        container = self.state_manager.get_current_container()
        if not container or "cubes" not in container:
            return

        for coord, data in container["cubes"].items():
            if "glyph" not in data:
                continue
            if coord in self.seen_glyphs:
                continue  # skip already triggered glyphs (optional)

            x, y, z = map(int, coord.split(","))
            self.executor.execute_glyph_at(x, y, z)
            self.seen_glyphs.add(coord)

    def run_loop(self, interval=2):
        print("🔁 Starting Glyph Runtime Loop...")
        while True:
            self.tick()
            time.sleep(interval)


if __name__ == "__main__":
    loop = GlyphRuntimeLoop()
    loop.run_loop()