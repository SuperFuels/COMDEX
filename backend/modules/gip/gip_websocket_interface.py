# File: backend/modules/gip/gip_websocket_interface.py

from fastapi import WebSocket
from .gip_executor import execute_gip_packet
from .gip_packet import GIPPacket
from .gip_packet_schema import validate_gip_packet
from ..glyphnet.glyphnet_terminal import run_symbolic_command
from ..websocket_manager import websocket_manager
import json

async def handle_gip_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                packet_dict = json.loads(raw_data)

                # 🧠 Symbolic Terminal Command
                if "command" in packet_dict:
                    cmd_result = run_symbolic_command(packet_dict["command"])
                    await websocket.send_text(json.dumps(cmd_result))
                    continue

                # ✅ Validate packet
                validate_gip_packet(packet_dict)

                # 🎯 GIP Packet Execution
                gip_packet = GIPPacket(**packet_dict)
                response = execute_gip_packet(gip_packet)

                await websocket.send_text(json.dumps({
                    "status": "ok",
                    "response": response
                }))

                # 📡 Broadcast execution result
                if response.get("status") == "ok":
                    symbol = packet_dict.get("symbol")
                    meta = packet_dict.get("meta", {})
                    await websocket_manager.broadcast(
                        message={
                            "event": "gip_execution",
                            "symbol": symbol,
                            "meta": meta,
                            "payload": response
                        },
                        tag="glyphnet"
                    )

            except Exception as e:
                await websocket.send_text(json.dumps({
                    "status": "error",
                    "message": str(e)
                }))
    except Exception:
        await websocket.close()