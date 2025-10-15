#!/usr/bin/env python3
# ──────────────────────────────────────────────
#  Tessaris • Stage 4 Coupling Test
#  Verifies LightWave → HST → HQCE integration
# ──────────────────────────────────────────────

import asyncio
import random
from datetime import datetime

from backend.modules.holograms.hst_generator import HSTGenerator
from backend.modules.holograms.hst_field_analyzer import HSTFieldAnalyzer
from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController
from backend.modules.holograms.sle_lightwave_bridge import SLELightWaveBridge


async def main():
    print("\n🌊 Starting SLE → HST LightWave coupling test...\n")

    # 1️⃣ Initialize HST + Feedback components
    hst = HSTGenerator()
    controller = MorphicFeedbackController()
    analyzer = HSTFieldAnalyzer(session_id=hst.session_id)

    # ✅ Corrected constructor arg: hst instead of hst_instance
    bridge = SLELightWaveBridge(hst=hst)

    # 2️⃣ Simulate a LightWave telemetry stream (10 frames)
    for tick in range(10):
        beam_packet = {
            "beam_id": f"beam_{tick}",
            "coherence": round(random.uniform(0.6, 0.98), 4),
            "phase_shift": round(random.uniform(-0.05, 0.05), 4),
            "entropy_drift": round(random.uniform(-0.02, 0.02), 4),
            "gain": round(random.uniform(0.8, 1.2), 3),
            "timestamp": datetime.utcnow().isoformat()
        }

        print(f"💡 Injecting LightWave beam {tick+1}/10 → coherence={beam_packet['coherence']:.3f}")

        # Feed into SLE→HST bridge (corrected function name)
        bridge.inject_beam_feedback(beam_packet)

        # Run morphic regulation cycle
        adjustment = controller.regulate(hst.field_tensor, list(hst.nodes.values()))
        print(f"⚙️  Morphic Regulation → {adjustment['status']} (ΔC={adjustment['correction']:+.4f})")

        # Push HST state to WebSocket bridge (optional)
        await asyncio.to_thread(bridge.broadcast_field_state)
        await asyncio.sleep(0.25)

    # 3️⃣ Run analyzer summary at the end
    summary = analyzer.summarize_field()
    print("\n📊 Final Analyzer Summary:")
    print(summary)
    print("\n✅ SLE→HST LightWave coupling test complete.\n")


if __name__ == "__main__":
    asyncio.run(main())