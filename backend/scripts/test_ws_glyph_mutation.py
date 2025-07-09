import asyncio
import json
import websockets

async def push_test():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        print("✅ Connected to WebSocket")
        message = {
            "type": "glyph_update",
            "coord": "2,3,1",
            "glyph": "🧠"
        }
        await websocket.send(json.dumps(message))
        print(f"📤 Sent test glyph: {message}")

asyncio.run(push_test())