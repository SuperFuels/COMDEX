import jax
import jax.numpy as jnp
from typing import List, Dict, Any


@jax.jit
def jax_join_waves_batch(wave_batch: jnp.ndarray) -> jnp.ndarray:
    """
    Perform batch wave interference using JAX for GPU acceleration.
    This function expects a 3D tensor of shape (B, H, W), where:
      - B is the batch size (number of wave fields)
      - H is the height of the wave grid
      - W is the width of the wave grid

    Returns a single 2D result grid (H, W) as the interference result.
    """
    return jnp.mean(wave_batch, axis=0)


def prepare_jax_input(waves: List[List[List[float]]]) -> jnp.ndarray:
    """
    Convert nested Python wave arrays to a JAX ndarray.
    Each wave should be a 2D array (H x W).
    The resulting JAX array will have shape (B, H, W).
    """
    return jnp.array(waves, dtype=jnp.float32)


def run_jax_interference(waves: List[List[List[float]]]) -> Dict[str, Any]:
    """
    Prepare input waves, run JAX interference, and return results with metadata.
    """
    import time

    # Prepare data
    batch_input = prepare_jax_input(waves)
    device = jax.devices()[0].device_kind
    shape = batch_input.shape

    # Run kernel
    start = time.time()
    result = jax_join_waves_batch(batch_input)
    end = time.time()

    return {
        "status": "ok",
        "interference_result": result.tolist(),
        "shape": shape,
        "device": device,
        "execution_time_ms": round((end - start) * 1000, 2)
    }