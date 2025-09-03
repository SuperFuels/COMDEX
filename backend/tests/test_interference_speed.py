# File: backend/tests/test_interference_speed.py

import time
import numpy as np
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.kernels.interference_kernels import join_waves, join_waves_batch

def generate_waves(n: int, length: int) -> list:
    return [
        WaveState(
            origin_trace=[f"src_{i}"],
            payload={
                "phase": np.random.rand(length) * 2 * np.pi,
                "amplitude": np.random.rand(length),
                "coherence": np.random.rand(),
                "timestamp": time.time()
            }
        )
        for i in range(n)
    ]

def benchmark_join_methods(n_waves=500, vector_length=128):
    waves = generate_waves(n_waves, vector_length)

    print(f"\n=== 🔬 Benchmarking {n_waves} waves × {vector_length} length ===")

    # Sequential join
    t1 = time.time()
    result_seq = join_waves(waves)
    t2 = time.time()
    print(f"[🔁 join_waves] Time: {(t2 - t1)*1000:.2f} ms")

    # Batch join
    t3 = time.time()
    result_batch = join_waves_batch(waves)
    t4 = time.time()
    print(f"[🚀 join_waves_batch] Time: {(t4 - t3)*1000:.2f} ms")

    # Compare results
    phase_diff = np.mean(np.abs(result_seq.payload["phase"] - result_batch.payload["phase"]))
    amp_diff = np.mean(np.abs(result_seq.payload["amplitude"] - result_batch.payload["amplitude"]))
    print(f"[Δ] Avg Phase Diff: {phase_diff:.6f}")
    print(f"[Δ] Avg Amplitude Diff: {amp_diff:.6f}")

if __name__ == "__main__":
    print("[🧪] Starting interference kernel benchmark...")
    benchmark_join_methods(n_waves=500, vector_length=128)
    benchmark_join_methods(n_waves=1000, vector_length=512)
    benchmark_join_methods(n_waves=2000, vector_length=1024)