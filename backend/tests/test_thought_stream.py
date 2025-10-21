import os
import json
import asyncio
import websockets

DEFAULT_URLS = [
    os.getenv("AION_THOUGHT_STREAM_URL"),
    "ws://0.0.0.0:8000/api/aion/thought-stream",
    "ws://0.0.0.0:8000/ws/thought-stream",
]

async def listen_thought_stream():
    for url in [u for u in DEFAULT_URLS if u]:
        print(f"🔌 Trying {url}")
        try:
            async with websockets.connect(url) as ws:
                print(f"✅ Connected to AION Thought Stream ({url})\n")
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    print("🧠 Event:", json.dumps(data, indent=2))
        except Exception as e:
            print(f"⚠️ Connection failed for {url}: {e}\n")
            await asyncio.sleep(1)
            continue
        break
    else:
        print("❌ No working WebSocket endpoints found.")

if __name__ == "__main__":
    try:
        asyncio.run(listen_thought_stream())
    except KeyboardInterrupt:
        print("\n🔌 Disconnected from AION Thought Stream.")