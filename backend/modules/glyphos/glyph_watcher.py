# backend/modules/runtime/glyph_watcher.py

from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.consciousness.state_manager import StateManager

class GlyphWatcher:
    def __init__(self, state_manager: StateManager):
        self.executor = GlyphExecutor(state_manager)
        self.state_manager = state_manager

    def scan_for_bytecode(self):
        """
        Scan the current container for glyphs with encoded bytecode.
        Execute or defer based on prefix.
        """
        container = self.state_manager.get_current_container()
        if not container:
            print("⚠️ No container loaded. Cannot scan for glyphs.")
            return

        cubes = container.get("cubes", {})
        if not cubes:
            print("⚠️ Container has no cubes.")
            return

        for coord, data in cubes.items():
            glyph = data.get("glyph", "")
            if glyph.startswith("⎇:") or glyph.startswith("⧉:"):
                try:
                    x, y, z = map(int, coord.split(","))
                    print(f"📦 Detected bytecode glyph at {coord}: {glyph}")
                    self.handle_bytecode(glyph, x, y, z)
                except ValueError:
                    print(f"❌ Invalid coordinate format: {coord}")

    def handle_bytecode(self, glyph: str, x: int, y: int, z: int):
        """
        Handle decoding and execution or deferral of bytecode glyphs.
        """
        if glyph.startswith("⎇:"):
            print(f"🧬 Executing decoded glyph at ({x},{y},{z})")
            decoded = glyph.replace("⎇:", "")  # Placeholder for decoding logic
            # TODO: Decode bytecode → real glyphs before executing
            self.executor.execute_glyph_at(x, y, z)
        elif glyph.startswith("⧉:"):
            print(f"📡 Deferred glyph at ({x},{y},{z}) → Remote logic not yet implemented.")