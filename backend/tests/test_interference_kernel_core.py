# File: backend/tests/test_interference_kernel_core.py

import time
import numpy as np
from backend.modules.glyphwave.kernels.interference_kernel_core import (
    WaveState,
    join_waves,
    join_waves_batch
)

def generate_random_waves(n: int, vector_length: int = 1) -> list:
    """Generate a list of WaveStates with random phase and amplitude."""
    return [
        WaveState(
            phase=np.random.uniform(-np.pi, np.pi),
            amplitude=np.random.uniform(0.5, 1.5),
            coherence=np.random.uniform(0.5, 1.0),
            origin_trace=[f"w{i}"],
        )
        for i in range(n)
    ]

def benchmark_join_methods(n_waves: int, vector_length: int = 1):
    print(f"\n=== 🔬 Benchmarking {n_waves} waves * {vector_length} length ===")

    waves = generate_random_waves(n_waves, vector_length)

    # Sequential join
    t1 = time.perf_counter()
    result_seq = join_waves(waves)
    t2 = time.perf_counter()
    print(f"[🔁 join_waves] Time: {(t2 - t1) * 1000:.2f} ms")

    # Batched join
    t3 = time.perf_counter()
    result_batch = join_waves_batch(waves)
    t4 = time.perf_counter()
    print(f"[🚀 join_waves_batch] Time: {(t4 - t3) * 1000:.2f} ms")

    # Compare results (very small numerical differences allowed)
    phase_diff = np.abs(result_seq.phase - result_batch.phase)
    amp_diff = np.abs(result_seq.amplitude - result_batch.amplitude)
    print(f"[Δ] Avg Phase Diff: {phase_diff:.6f}")
    print(f"[Δ] Avg Amplitude Diff: {amp_diff:.6f}")

    assert phase_diff < 1e-8, "Phase mismatch"
    assert amp_diff < 1e-8, "Amplitude mismatch"


if __name__ == "__main__":
    print("[🧪] Starting pinned interference kernel benchmark...")

    benchmark_join_methods(n_waves=500)
    benchmark_join_methods(n_waves=1000)
    benchmark_join_methods(n_waves=2000)