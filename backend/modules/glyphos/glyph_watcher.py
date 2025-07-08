# glyph_watcher.py

from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.consciousness.state_manager import StateManager

class GlyphWatcher:
    def __init__(self, state_manager: StateManager):
        self.executor = GlyphExecutor(state_manager)
        self.state_manager = state_manager

    def scan_for_bytecode(self):
        container = self.state_manager.get_current_container()
        cubes = container.get("cubes", {})

        for coord, data in cubes.items():
            glyph = data.get("glyph", "")
            if glyph.startswith("⎇:") or glyph.startswith("⧉:"):
                x, y, z = map(int, coord.split(","))
                print(f"📦 Detected bytecode glyph at {coord}: {glyph}")
                self.handle_bytecode(glyph, x, y, z)

    def handle_bytecode(self, glyph: str, x: int, y: int, z: int):
        if glyph.startswith("⎇:"):
            print(f"🧬 Decoding and executing bytecode at ({x},{y},{z})")
            decoded = glyph.replace("⎇:", "")  # placeholder
            # Here you would plug in bytecode → glyph decompression
            self.executor.execute_glyph_at(x, y, z)
        elif glyph.startswith("⧉:"):
            print(f"📡 Deferring remote glyph at ({x},{y},{z}) → Placeholder")
            # Could fetch glyph logic remotely or delay activation