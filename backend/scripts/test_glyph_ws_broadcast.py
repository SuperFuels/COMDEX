# backend/scripts/test_glyph_ws_broadcast.py

import asyncio
from backend.modules.websocket_manager import websocket_manager

# Simulated glyph event
test_glyph_event = {
    "type": "glyph_activation",
    "container": "fractal.cube",
    "glyph": "ΣΩ-33",
    "status": "activated",
    "message": "Test glyph activation broadcasted from script"
}

def test_broadcast_glyph_event():
    print("📡 Broadcasting glyph event via WebSocket...")
    asyncio.run(websocket_manager.broadcast(test_glyph_event))
    print("✅ Glyph event sent. Check frontend listener + terminal logs.")

if __name__ == "__main__":
    test_broadcast_glyph_event()