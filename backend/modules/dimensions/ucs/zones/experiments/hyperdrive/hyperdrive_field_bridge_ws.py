# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_field_bridge_ws.py

"""
🌐 FieldBridge WebSocket Server (Hyperdrive)
----------------------------------------
Runs on the Raspberry Pi to:
    • Expose live PWM coil control (frequency & duty)
    • Provide ADC feedback (voltage/current sensing)
    • Enable closed-loop tuning from remote clients (e.g., MacBook HyperdriveEngine)
    • Secure connection with optional auth token
"""

import asyncio
import json
import websockets
import threading
from typing import Dict, Any

from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_field_bridge import FieldBridge


class FieldBridgeWSServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, safe_mode: bool = False, auth_token: str = None):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.bridge = FieldBridge(safe_mode=safe_mode)
        self.clients = set()
        self.running = False

    # ---------------------------------------------------------
    # 🌐 WebSocket Handler
    # ---------------------------------------------------------
    async def handler(self, websocket):
        print(f"🔌 Client connected: {websocket.remote_address}")
        self.clients.add(websocket)

        try:
            async for msg in websocket:
                await self._process_message(websocket, msg)
        except websockets.exceptions.ConnectionClosed:
            print(f"❌ Client disconnected: {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)

    # ---------------------------------------------------------
    # 📥 Process Incoming Commands
    # ---------------------------------------------------------
    async def _process_message(self, websocket, msg: str):
        try:
            data = json.loads(msg)

            # ✅ Auth check
            if self.auth_token and data.get("token") != self.auth_token:
                await websocket.send(json.dumps({"type": "error", "message": "Unauthorized"}))
                return

            cmd = data.get("cmd")
            if cmd == "emit_wave":
                freq = float(data["freq"])
                duty = float(data["duty"])
                self.bridge.emit_waveform(freq, duty)
                await websocket.send(json.dumps({"type": "ack", "message": f"Wave emitted {freq}Hz @ {duty}%"}))

            elif cmd == "read_feedback":
                voltage = self.bridge.read_feedback()
                await websocket.send(json.dumps({"type": "feedback", "voltage": voltage}))

            elif cmd == "auto_calibrate":
                target_v = float(data.get("target_voltage", 1.0))
                adj = self.bridge.auto_calibrate(target_voltage=target_v)
                await websocket.send(json.dumps({"type": "calibration", "adjustment": adj}))

            elif cmd == "shutdown":
                self.bridge.shutdown()
                await websocket.send(json.dumps({"type": "ack", "message": "FieldBridge shutdown"}))

            else:
                await websocket.send(json.dumps({"type": "error", "message": f"Unknown command: {cmd}"}))

        except Exception as e:
            await websocket.send(json.dumps({"type": "error", "message": str(e)}))

    # ---------------------------------------------------------
    # 🚀 Server Start
    # ---------------------------------------------------------
    async def start(self):
        print(f"🌐 FieldBridge WS Server starting on ws://{self.host}:{self.port}")
        self.running = True
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # Run forever

    def run_background(self):
        """Run server in background thread (non-blocking)."""
        def runner():
            asyncio.run(self.start())
        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        print("🟢 FieldBridge WS running in background thread.")

    # ---------------------------------------------------------
    # 🛑 Stop Server
    # ---------------------------------------------------------
    def stop(self):
        print("🔻 Stopping FieldBridge WS server...")
        self.bridge.shutdown()
        self.running = False


# ---------------------------------------------------------
# 🔧 Entry Point (Standalone Pi Service)
# ---------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FieldBridge WebSocket Server (Hyperdrive)")
    parser.add_argument("--host", default="0.0.0.0", help="WebSocket host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument("--safe", action="store_true", help="Run in safe (simulated) mode")
    parser.add_argument("--token", type=str, help="Optional auth token")

    args = parser.parse_args()
    server = FieldBridgeWSServer(host=args.host, port=args.port, safe_mode=args.safe, auth_token=args.token)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        server.stop()
        print("\n🛑 Server stopped.")