# glyph_executor.py

from backend.modules.glyphos.glyph_parser import parse_glyph
from backend.modules.glyphos.glyph_dispatcher import GlyphDispatcher
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.dna_chain.dna_switch import register_dna_switch


class GlyphExecutor:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.dispatcher = GlyphDispatcher(state_manager)
        self.active_container = self.state_manager.get_current_container()

    def read_glyph_at(self, x: int, y: int, z: int) -> str:
        cube = self.active_container.get("cubes", {}).get(f"{x},{y},{z}", {})
        return cube.get("glyph", "")

    def execute_glyph_at(self, x: int, y: int, z: int):
        glyph = self.read_glyph_at(x, y, z)
        if not glyph:
            print(f"⚠️ No glyph found at ({x},{y},{z})")
            return

        parsed = parse_glyph(glyph)
        print(f"🔍 Parsed glyph: {parsed}")
        self.dispatcher.dispatch(parsed)


register_dna_switch(__file__)