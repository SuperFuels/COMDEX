# File: backend/modules/gip/gip_test_runner.py

import json
from .gip_packet import create_gip_packet
from .gip_executor import execute_gip_packet

def run_test():
    print("\n[GlyphNet Test] Running symbolic_thought packet test...")
    packet = create_gip_packet(
        packet_type="symbolic_thought",
        channel="luxnet",
        payload={
            "glyphs": [
                {"glyph": "✦", "args": {"goal": "test_phase1"}},
                {"glyph": "🧠", "args": {"reflect": True}}
            ]
        }
    )
    result = execute_gip_packet(packet)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    run_test()
