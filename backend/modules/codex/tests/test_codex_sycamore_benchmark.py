# 📁 backend/modules/codex/tests/test_codex_sycamore_benchmark.py

import time
import numpy as np
from backend.modules.wave.physics.interference_kernel_core import join_waves_batch

import pytest

try:
    from backend.modules.wave.physics.interference_kernel_core import join_waves_batch
except ModuleNotFoundError:
    pytest.skip("wave.physics module not present in this repo layout", allow_module_level=True)

def run_sycamore_scale_benchmark(num_waves=10_000, length=1):
    print("\n=== ⚡ Running Sycamore-Scale Interference Kernel Benchmark ===\n")
    
    # 🔢 Generate symbolic beam array (phases + amplitudes)
    phases = np.random.uniform(-np.pi, np.pi, size=(num_waves, length)).astype(np.float32)
    amplitudes = np.random.uniform(0.5, 1.5, size=(num_waves, length)).astype(np.float32)

    # 🧪 Run vectorized interference collapse
    start = time.perf_counter()
    result_wave = join_waves_batch(phases, amplitudes)
    end = time.perf_counter()

    # 📊 Output results
    total_time = (end - start) * 1000  # ms
    print(f"🔢 Waves: {num_waves} | Length: {length}")
    print(f"⏱️ Collapse Time: {total_time:.2f} ms")
    print(f"📐 Result Phase (first 5):     {np.round(result_wave['phase'][:5], 4)}")
    print(f"📐 Result Amplitude (first 5): {np.round(result_wave['amplitude'][:5], 4)}")
    print("\n✅ Sycamore-scale vectorized interference benchmark complete.\n")

if __name__ == "__main__":
    run_sycamore_scale_benchmark()