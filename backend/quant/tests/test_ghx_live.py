# ===============================
# 📁 backend/quant/tests/test_ghx_live.py
# ===============================
"""
🧭 GHX Live Telemetry Stream Test
---------------------------------
Continuously emits coherence / resonance metrics from the Tessaris runtime
via ResonanceTelemetry -> GHXFeedbackBridge.

Demonstrates live feedback streaming from symbolic quantum runtime to GHX/QFC layer.
"""

import asyncio
import time
import json
from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry
from backend.modules.visualization.ghx_feedback_bridge import GHXFeedbackBridge


class MockRuntime:
    """Simulated GlyphWaveRuntime providing dynamic coherence metrics."""

    def __init__(self):
        self.parameters = {
            "resonance_mode": "synchronized",
            "feedback_gain": 0.95,
            "stability": 0.982,
        }
        self.tele = ResonanceTelemetry()

    def metrics(self):
        """Generate synthetic coherence metrics packet."""
        data = self.tele.emit()
        # Enrich with simulated runtime details
        data["runtime_time"] = time.time()
        data["coherence_score"] = round(0.95 + 0.05 * (time.time() % 1), 3)
        return data


async def main():
    print("🌈 [Tessaris] GHX Live Telemetry Relay - starting stream...\n")
    runtime = MockRuntime()
    bridge = GHXFeedbackBridge()

    async def print_packet(packet):
        print("📡 GHX Packet:", json.dumps(packet, indent=2))

    # override bridge callback for printing
    bridge.send_callback = print_packet

    # run live monitor for 5 samples @ 1s interval
    await bridge.live_monitor(runtime, interval=1.0, max_samples=5)

    print("\n✅ Stream test completed. GHX feedback bridge functional.\n")


if __name__ == "__main__":
    asyncio.run(main())