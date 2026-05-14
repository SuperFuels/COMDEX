# ✅ WEBSOCKET RUNTIME LOOP - tessaris_ws_runtime.py
import asyncio
import json
import websockets
from backend.modules.tessaris.tessaris_engine import TessarisEngine

TESSARIS_WS_URI = "ws://localhost:8000/ws/tessaris"  # Update as needed
engine = TessarisEngine(container_id="ws_loop")

async def tessaris_ws_handler():
    async with websockets.connect(TESSARIS_WS_URI) as websocket:
        print("[🌐] Connected to Tessaris WebSocket loop")
        while True:
            message = await websocket.recv()
            try:
                cube = json.loads(message)
                print(f"[📦] Received cube: {cube}")
                engine.process_triggered_cube(cube, source="websocket")
                
                # Expand and execute thought
                thought_id = list(engine.active_thoughts.keys())[-1]
                engine.expand_thought(thought_id, depth=2)
                branch = engine.active_branches[-1] if engine.active_branches else None
                if branch:
                    engine.execute_branch(branch)

            except Exception as e:
                print(f"[⚠️] Error handling message: {e}")

if __name__ == "__main__":
    asyncio.run(tessaris_ws_handler())