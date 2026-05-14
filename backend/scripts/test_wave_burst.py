# File: backend/scripts/test_wave_burst.py
import asyncio
import random
from backend.modules.glyphwave.telemetry_handler import TelemetryHandler
from backend.modules.glyphwave.kernels.superposition_kernels import compose_superposition
from backend.modules.glyphwave.kernels.measurement_kernels import measure_wave
from backend.modules.glyphwave.core.wave_state import WaveState

async def main():
    handler = TelemetryHandler()
    await handler.connect()

    print("\n⚡ Running wave burst coherence test...\n")

    for i in range(5):
        # ✅ Create WaveStates using glyph_data, not direct phase/amplitude args
        waves = [
            WaveState(glyph_data={
                "phase": random.uniform(0, 2 * 3.14159),
                "amplitude": random.uniform(0.5, 1.0),
                "coherence": random.uniform(0.8, 1.0),
                "label": f"wave_{i}_{j}"
            })
            for j in range(3)
        ]

        combined = compose_superposition(waves)
        result = measure_wave(combined, policy="probabilistic")
        metrics = await handler.collect_metrics()

        print(f"[Tick {i}] coherence={metrics['coherence_stability']:.3f}, "
              f"collapse_rate={metrics['collapse_rate']:.3f}, "
              f"pattern_sqi={metrics.get('pattern_sqi', 0):.3f}")
        await asyncio.sleep(1.0)

    await handler.disconnect()
    print("\n✅ Wave burst test completed.\n")

if __name__ == "__main__":
    asyncio.run(main())