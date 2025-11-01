#!/usr/bin/env python3
# ──────────────────────────────────────────────
#  Tessaris * Stage 4 Coupling Integration Test
#  Verifies live LightWave -> HST -> HQCE coherence loop
# ──────────────────────────────────────────────

import asyncio
import random
import time
from datetime import datetime

from backend.modules.holograms.hst_generator import HSTGenerator
from backend.modules.holograms.hst_field_analyzer import HSTFieldAnalyzer
from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController
from backend.modules.holograms.sle_lightwave_bridge import SLELightWaveBridge


async def main():
    print("\n🌊 Starting Stage 4 LightWave -> HST coupling test...\n")

    # 1️⃣ Initialize components
    hst = HSTGenerator()
    feedback = MorphicFeedbackController()
    analyzer = HSTFieldAnalyzer(session_id=hst.session_id)
    bridge = SLELightWaveBridge(hst=hst)

    print(f"🧠 Initialized LightWave -> HST bridge session -> {bridge.session_id}\n")

    # 2️⃣ Simulate incoming LightWave feedback frames
    for tick in range(10):
        beam_packet = {
            "beam_id": f"beam_{tick}",
            "coherence": round(random.uniform(0.6, 0.97), 4),
            "phase_shift": round(random.uniform(-0.05, 0.05), 4),
            "entropy_drift": round(random.uniform(-0.02, 0.02), 4),
            "gain": round(random.uniform(0.85, 1.15), 3),
            "timestamp": datetime.utcnow().isoformat(),
        }

        print(f"💡 Injecting LightWave beam {tick+1}/10 -> coherence={beam_packet['coherence']:.3f}")

        # Inject feedback into bridge
        adjustment = bridge.inject_beam_feedback(beam_packet)

        # Apply additional morphic regulation
        regulation = feedback.regulate(hst.field_tensor, list(hst.nodes.values()))
        print(f"⚙️ Morphic Regulation -> {regulation['status']} (ΔC={regulation['correction']:+.4f})")

        # Optional: broadcast after each tick
        await asyncio.to_thread(bridge.broadcast_field_state)
        await asyncio.sleep(0.25)

    # 3️⃣ Field Analyzer summary
    summary = analyzer.summarize_field()
    print("\n📊 Final Analyzer Summary:")
    print(summary)

    # 4️⃣ Snapshot summary export
    state = bridge.summarize_state()
    print("\n🧩 Bridge Diagnostic State:")
    print(state)

    print("\n✅ SLE -> HST LightWave coupling test complete.\n")


if __name__ == "__main__":
    asyncio.run(main())