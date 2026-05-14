"""
Tessaris * QQC v0.5 - Symatics Lightwave Engine Test
Test Script: Wave Modulation Evolution
----------------------------------------------------
Runs each Symatics operator (⊕, ↔, μ, ⟲, π) through
the VirtualWaveEngine and logs amplitude/phase/freq
evolution + coherence decay per tick.

Usage:
    python scripts/test_wave_modulation.py
"""

import time
import logging
from backend.codexcore_virtual.virtual_wave_engine import VirtualWaveEngine
from backend.modules.glyphwave.core.wave_state import WaveState

# ──────────────────────────────────────────────
# Setup logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Operator test sequence
# ──────────────────────────────────────────────
TEST_OPERATORS = ["⊕", "↔", "μ", "⟲", "π"]

def run_wave_modulation_test():
    print("\n🌊 [TEST] Starting Symatics Lightwave modulation test (QQC v0.5)\n")

    # Initialize engine + wave
    engine = VirtualWaveEngine(container_id="sle.modulation_test")
    wave = WaveState()
    wave.id = "test_wave_001"
    engine.attach_wave(wave)

    # Run through each operator
    for opcode in TEST_OPERATORS:
        print(f"\n🔸 Running operator: {opcode}")
        instructions = [{"opcode": opcode}]
        engine.load_wave_program(instructions)

        # Run a short 3-tick loop per operator
        for i in range(3):
            wave_before = (wave.amplitude, wave.phase, wave.frequency, wave.coherence)
            engine._apply_symatics_modulation(wave, opcode)
            wave.evolve()
            wave_after = (wave.amplitude, wave.phase, wave.frequency, wave.coherence)

            logger.info(
                f"[Tick {i+1}] opcode={opcode} | "
                f"amp {wave_before[0]:.3f}->{wave_after[0]:.3f}, "
                f"phase {wave_before[1]:.3f}->{wave_after[1]:.3f}, "
                f"freq {wave_before[2]:.3f}->{wave_after[2]:.3f}, "
                f"coh {wave_before[3]:.3f}->{wave_after[3]:.3f}"
            )
            time.sleep(0.1)

    print("\n✅ [TEST COMPLETE] Wave modulation sequence executed successfully.\n")


if __name__ == "__main__":
    run_wave_modulation_test()