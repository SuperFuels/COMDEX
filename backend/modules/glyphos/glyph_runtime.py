# glyph_runtime.py

import time
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.consciousness.state_manager import StateManager


class GlyphRuntime:
    def __init__(self, state_manager: StateManager):
        self.executor = GlyphExecutor(state_manager)
        self.state_manager = state_manager
        self.interval = 1.0  # seconds between scans

    def tick(self):
        container = self.state_manager.get_current_container()
        cubes = container.get("cubes", {})
        for coord, data in cubes.items():
            glyph = data.get("glyph", "")
            if glyph:
                x, y, z = map(int, coord.split(","))
                print(f"⏱️ Runtime tick found glyph at ({coord}) → Executing")
                self.executor.execute_glyph_at(x, y, z)

    def run(self, duration_seconds=10):
        print(f"🌀 Starting GlyphRuntime loop for {duration_seconds}s...")
        start = time.time()
        while time.time() - start < duration_seconds:
            self.tick()
            time.sleep(self.interval)
        print("✅ GlyphRuntime loop complete.")