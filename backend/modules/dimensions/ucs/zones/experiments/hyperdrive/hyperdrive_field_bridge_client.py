# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_field_bridge_client.py

"""
🌐 FieldBridge Client (Adaptive Feedback Control + Live HUD + Trend Tuning)
-----------------------------------------------------
    * Streams exhaust wave commands from HyperdriveEngine to Pi FieldBridge
    * Auto-harmonics + burst mode per exhaust tick
    * Adaptive tuning: dynamically adjusts drive params based on live coil feedback
    * Live HUD: real-time voltage, duty, harmonics visualization
    * Trend-based harmonics scaling: stabilize voltage oscillations using HUD metrics
"""

import asyncio
import json
import websockets
from typing import Optional, Callable

from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_field_bridge_hud import FieldBridgeHUD


class FieldBridgeClient:
    def __init__(self, uri: str = "ws://raspberrypi.local:8765", token: Optional[str] = None, target_voltage: float = 1.0):
        self.uri = uri
        self.token = token
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.target_voltage = target_voltage
        self.last_feedback_voltage: Optional[float] = None
        self.on_feedback: Optional[Callable[[float], None]] = None

        # ✅ Live HUD initialization
        self.hud = FieldBridgeHUD(max_points=300, target_voltage=target_voltage)
        self.last_duty = 0.0
        self.last_harmonics = 1

    # ---------------------------------------------------------
    # 🌐 Connect to Pi WebSocket
    # ---------------------------------------------------------
    async def connect(self):
        print(f"🔌 Connecting to FieldBridge at {self.uri}...")
        self.websocket = await websockets.connect(self.uri)
        self.connected = True
        print("✅ Connected to FieldBridge WS.")

    # ---------------------------------------------------------
    # 🔥 Emit Waveform (Auto-Harmonics + Burst + Adaptive Feedback + Trend Tuning)
    # ---------------------------------------------------------
    async def emit_exhaust_wave(self, phase: float, energy: float):
        if not self.connected:
            await self.connect()

        freq = 100 + (phase * 50)
        duty = min(max((energy * 10) % 100, 5), 95)

        # Base harmonics selection
        harmonics = 1
        if abs(phase) > 0.5:
            harmonics = 2
        if abs(phase) > 0.85:
            harmonics = 3

        burst = energy > 0.4

        # ✅ Adaptive feedback tuning (coil voltage error)
        if self.last_feedback_voltage is not None:
            error = self.target_voltage - self.last_feedback_voltage
            if abs(error) > 0.05:
                duty = max(5, min(95, duty + (error * 20)))
                if error > 0.1 and harmonics < 3:
                    harmonics += 1
                elif error < -0.1 and harmonics > 1:
                    harmonics -= 1

        # ✅ Trend-based harmonics scaling (HUD-driven stability control)
        metrics = self.hud.get_trend_metrics(window=20)
        if metrics["variance"] < 0.002:  # Very stable, reduce complexity
            harmonics = max(1, harmonics - 1)
            burst = False
        elif metrics["variance"] > 0.01 or abs(metrics["slope"]) > 0.002:  # Oscillating/drifting
            harmonics = min(3, harmonics + 1)
            burst = True

        self.last_duty = duty
        self.last_harmonics = harmonics

        payload = {
            "cmd": "emit_wave",
            "freq": round(freq, 2),
            "duty": round(duty, 1),
            "harmonics": harmonics,
            "burst": burst,
            "token": self.token
        }

        print(f"🎵 Exhaust Wave -> freq={freq:.1f}Hz | duty={duty:.1f}% | harmonics={harmonics} | burst={burst}")
        await self.websocket.send(json.dumps(payload))

    # ---------------------------------------------------------
    # 🔎 Request ADC Feedback (HUD Integrated)
    # ---------------------------------------------------------
    async def request_feedback(self):
        if not self.connected:
            await self.connect()

        await self.websocket.send(json.dumps({"cmd": "read_feedback", "token": self.token}))
        response = await self.websocket.recv()
        data = json.loads(response)
        if data.get("type") == "feedback":
            voltage = data["voltage"]
            self.last_feedback_voltage = voltage
            print(f"📡 Live Coil Feedback: {voltage:.3f} V (target={self.target_voltage:.2f}V)")

            # ✅ Update HUD
            self.hud.add_data_point(voltage, self.last_duty, self.last_harmonics)

            if self.on_feedback:
                self.on_feedback(voltage)
            return voltage
        return None

    # ---------------------------------------------------------
    # 🔄 Continuous Exhaust Loop Integration (Adaptive + HUD)
    # ---------------------------------------------------------
    async def exhaust_loop(self, engine_ref, feedback_interval: float = 0.5):
        while True:
            if engine_ref.resonance_log and engine_ref.exhaust_log:
                phase = engine_ref.resonance_log[-1]
                energy = engine_ref.exhaust_log[-1]["energy"]
                await self.emit_exhaust_wave(phase, energy)

            await asyncio.sleep(feedback_interval)
            await self.request_feedback()

    # ---------------------------------------------------------
    # 🛠 Auto-Calibrate
    # ---------------------------------------------------------
    async def auto_calibrate(self, target_voltage: float = 1.0):
        self.target_voltage = target_voltage
        print(f"🎯 Target voltage set to {self.target_voltage:.2f}V (adaptive loop will adjust automatically).")

    # ---------------------------------------------------------
    # 📴 Shutdown
    # ---------------------------------------------------------
    async def shutdown(self):
        if self.connected and self.websocket:
            await self.websocket.send(json.dumps({"cmd": "shutdown", "token": self.token}))
            await self.websocket.close()
            self.connected = False
            print("🔻 FieldBridge client disconnected.")

    # ---------------------------------------------------------
    # 🖥 HUD Runner
    # ---------------------------------------------------------
    async def run_hud(self):
        await self.hud.run()


# ---------------------------------------------------------
# 🔧 Example Usage
# ---------------------------------------------------------
if __name__ == "__main__":
    import argparse
    from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.hyperdrive_engine import HyperdriveEngine
    from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer

    parser = argparse.ArgumentParser(description="FieldBridge Client (Adaptive + HUD + Trend Tuning)")
    parser.add_argument("--uri", default="ws://raspberrypi.local:8765", help="Pi WebSocket URI")
    parser.add_argument("--token", type=str, help="Auth token if required")
    parser.add_argument("--target_voltage", type=float, default=1.0, help="Desired coil voltage target (V)")
    args = parser.parse_args()

    container = SymbolicExpansionContainer(seed_glyphs=["⚛", "🌌"])
    engine = HyperdriveEngine(container=container, safe_mode=True)
    client = FieldBridgeClient(uri=args.uri, token=args.token, target_voltage=args.target_voltage)

    async def run():
        await client.connect()
        asyncio.create_task(client.exhaust_loop(engine))
        asyncio.create_task(client.run_hud())

        while True:
            engine.tick()
            await asyncio.sleep(0.05)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        asyncio.run(client.shutdown())