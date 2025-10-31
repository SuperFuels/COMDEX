#!/usr/bin/env python3
import asyncio
import websockets

from y_py import YDoc
from ypy_websocket.websocket_server import WebsocketServer, YRoom
from ypy_websocket.ystore import SQLiteYStore

# === CRDT persistence for Photon buffer ===
store = SQLiteYStore("photon_crdt.sqlite")
ydoc = YDoc()

room = YRoom(ydoc, ystore=store)

server = WebsocketServer(room)  # ✅ single-room mode


async def main():
    host = "0.0.0.0"
    port = 8765
    print(f"✅ Photon CRDT server live → ws://{host}:{port}/")

    async with websockets.serve(server.serve, host, port):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())