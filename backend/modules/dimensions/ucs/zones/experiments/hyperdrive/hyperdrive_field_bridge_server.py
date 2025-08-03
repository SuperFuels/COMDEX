# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_field_bridge_server.py

"""
🌐 FieldBridge Server (Raspberry Pi)
-----------------------------------------------------
Runs on the Raspberry Pi to interface with the QWave FieldBridge hardware:
    • Async WebSocket server for real-time control from MacBook
    • Supports emit_wave, harmonics, burst mode, feedback read, and auto-calibration
    • Secure token-based authentication (optional)
    • Closes the loop for live coil feedback and tuning
"""

import asyncio
import json
import websockets
from typing import Optional

from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_field_bridge import FieldBridge
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_field_bridge_client import FieldBridgeClient

# ---------------------------------------------------------
# ⚙ Configuration
# ---------------------------------------------------------
HOST = "0.0.0.0"
PORT = 8765
AUTH_TOKEN: Optional[str] = None  # Set to a string to enable token auth (e.g., "my-secret-token")

# Initialize hardware bridge
field_bridge = FieldBridge(safe_mode=False, dual_coil=True)

# ---------------------------------------------------------
# 🔑 Authentication Helper
# ---------------------------------------------------------
def check_auth(payload: dict) -> bool:
    if AUTH_TOKEN is None:
        return True  # No auth required
    return payload.get("token") == AUTH_TOKEN

# ---------------------------------------------------------
# 🌐 WebSocket Handler
# ---------------------------------------------------------
async def handler(websocket, path):
    print("🔌 Client connected.")
    try:
        async for msg in websocket:
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            if not check_auth(data):
                await websocket.send(json.dumps({"type": "error", "message": "Unauthorized"}))
                continue

            cmd = data.get("cmd")

            # 🔥 Emit Waveform Command
            if cmd == "emit_wave":
                freq = float(data.get("freq", 100))
                duty = float(data.get("duty", 50))
                harmonics = int(data.get("harmonics", 1))
                burst = bool(data.get("burst", False))
                print(f"🎵 Emit: freq={freq}Hz duty={duty}% harmonics={harmonics} burst={burst}")
                field_bridge.emit_multi_harmonic(base_freq=freq, duty=duty, harmonics=harmonics, burst=burst)
                await websocket.send(json.dumps({"type": "ack", "cmd": "emit_wave"}))

            # 📡 Read Feedback Command
            elif cmd == "read_feedback":
                voltage = field_bridge.read_feedback()
                await websocket.send(json.dumps({"type": "feedback", "voltage": voltage}))

            # ⚖ Auto-Calibrate Command
            elif cmd == "auto_calibrate":
                target_voltage = float(data.get("target_voltage", 1.0))
                adjustment = field_bridge.auto_calibrate(target_voltage=target_voltage)
                await websocket.send(json.dumps({
                    "type": "calibration",
                    "target_voltage": target_voltage,
                    "adjustment": adjustment
                }))

            # 🔻 Shutdown Command
            elif cmd == "shutdown":
                print("🔻 Shutdown command received. Stopping coils.")
                field_bridge.shutdown()
                await websocket.send(json.dumps({"type": "shutdown"}))
                break

            else:
                await websocket.send(json.dumps({"type": "error", "message": f"Unknown cmd: {cmd}"}))

    except websockets.ConnectionClosed:
        print("🔌 Client disconnected.")
    finally:
        field_bridge.shutdown()


# ---------------------------------------------------------
# 🚀 Start WebSocket Server
# ---------------------------------------------------------
async def main():
    print(f"🌐 Starting FieldBridge WebSocket server on ws://{HOST}:{PORT}")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Server stopped by user.")
        field_bridge.shutdown()