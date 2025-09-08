"""
gpu_collapse_accelerator.py
============================

Accelerated symbolic beam collapse engine using GPU-backed vector math.
Supports both NumPy (CPU fallback) and JAX (GPU/TPU) backends.

Used in SQI for high-speed symbolic wavefunction resolution and collapse.
"""

import logging
import numpy as np

try:
    import jax.numpy as jnp
    from jax import random, jit
    JAX_AVAILABLE = True
except ImportError:
    JAX_AVAILABLE = False

logger = logging.getLogger(__name__)

# -------------------------------
# Collapse Kernel Config
# -------------------------------
DEFAULT_TEMPERATURE = 0.85
EPSILON = 1e-9


# -------------------------------
# Utility: Softmax
# -------------------------------

def softmax(x, temperature=1.0):
    x = x - np.max(x)  # stability
    e_x = np.exp(x / max(temperature, EPSILON))
    return e_x / (np.sum(e_x) + EPSILON)


def softmax_jax(x, temperature=1.0):
    x = x - jnp.max(x)
    e_x = jnp.exp(x / max(temperature, EPSILON))
    return e_x / (jnp.sum(e_x) + EPSILON)


# -------------------------------
# Collapse Engine (CPU)
# -------------------------------

def collapse_symbolic_wave_cpu(weights: np.ndarray, options: list, temperature=DEFAULT_TEMPERATURE):
    """
    Collapses symbolic wave using softmax-weighted probability selection (CPU/NumPy).
    """
    if len(weights) != len(options):
        raise ValueError("Weights and options length mismatch")

    probs = softmax(np.array(weights), temperature)
    choice = np.random.choice(len(options), p=probs)
    logger.debug(f"[Collapse CPU] ⬇️ Chose option {choice} with p={probs[choice]:.4f}")
    return options[choice], probs.tolist()


# -------------------------------
# Collapse Engine (GPU/JAX)
# -------------------------------

@jit
def _collapse_symbolic_wave_jax(weights_jnp, temperature=DEFAULT_TEMPERATURE):
    probs = softmax_jax(weights_jnp, temperature)
    return probs


def collapse_symbolic_wave_gpu(weights: list, options: list, temperature=DEFAULT_TEMPERATURE, seed=None):
    if not JAX_AVAILABLE:
        raise RuntimeError("JAX is not installed — install it or use the CPU fallback.")

    if len(weights) != len(options):
        raise ValueError("Weights and options length mismatch")

    key = random.PRNGKey(seed or np.random.randint(0, 1e6))
    weights_jnp = jnp.array(weights, dtype=jnp.float32)
    probs = _collapse_symbolic_wave_jax(weights_jnp, temperature)
    idx = random.choice(key, jnp.arange(len(options)), p=probs)
    logger.debug(f"[Collapse GPU] ⚡ Chose option {int(idx)} with p={float(probs[idx]):.4f}")
    return options[int(idx)], list(probs)