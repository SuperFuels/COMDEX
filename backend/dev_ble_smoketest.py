# backend/dev_ble_smoketest.py

from backend.modules.glyphnet.glyph_transport_switch import route_glyph_packet

if __name__ == "__main__":
    res = route_glyph_packet(
        glyphs=[{"op": "⊕", "value": "test_ble"}],
        transport="ble",
        metadata={"sender": "dev-node-1"},
    )
    print(res)