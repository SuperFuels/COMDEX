# File: backend/modules/glyphwave/gpu/gpu_kernel_test_rig.py

import time
import jax
import jax.numpy as jnp

from backend.modules.glyphwave.gpu.jax_interference_kernel import jax_join_waves_batch


def run_jax_gpu_test(batch_size=64, glyph_size=128):
    """
    Executes a symbolic batch join using JAX (GPU if available) and returns timing + metrics.
    """
    device = jax.devices()[0]
    print(f"[🧠] Running on device: {device}")

    # Simulate a batch of symbolic wave glyphs (as vectors)
    wave_batch = jnp.ones((batch_size, glyph_size), dtype=jnp.float32)

    # Run benchmark
    start = time.time()
    result = jax_join_waves_batch(wave_batch)
    jax.block_until_ready(result)
    elapsed = (time.time() - start) * 1000  # ms

    print("\n[🚀 JAX GPU Test Complete]")
    print(f"Batch Size: {batch_size}, Glyph Size: {glyph_size}")
    print(f"⏱️ Execution Time: {elapsed:.2f} ms")
    print(f"📐 Output Shape: {result.shape}")

    return {
        "status": "ok",
        "backend": str(device),
        "elapsed_ms": elapsed,
        "output_shape": result.shape,
    }


if __name__ == "__main__":
    run_jax_gpu_test()