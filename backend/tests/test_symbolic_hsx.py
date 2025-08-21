# File: backend/tests/test_symbolic_hsx.py
import json
from backend.modules.hologram.symbolic_hsx_bridge import SymbolicHSXBridge
from backend.modules.hologram.holographic_renderer import HolographicRenderer

def run_test(path: str, observer: str = "tester"):
    with open(path, "r", encoding="utf-8") as f:
        packet = json.load(f)

    renderer = HolographicRenderer(packet, observer_id=observer, lazy_mode=False)
    field = renderer.render_glyph_field()

    print(f"🔮 Rendered {len(field)} glyphs for observer '{observer}'")

    SymbolicHSXBridge.broadcast_glyphs(field, observer=observer)
    print("🛰️ Broadcast trails to HSX overlay.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_symbolic_hsx.py <path_to_ghx_packet.json>")
    else:
        run_test(sys.argv[1])