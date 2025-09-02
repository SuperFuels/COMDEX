# File: backend/modules/glyphwave/kernels/measurement_kernels.py
import random
from typing import Dict, Optional
from backend.modules.glyphwave.core.wave_state import WaveState


def measure_wave(wave: WaveState, policy: str = "greedy", selector: Optional[Dict] = None) -> Dict:
    """
    Collapse a WaveState according to a specified measurement policy.

    Returns a dictionary with measurement results and metadata.
    """
    result = {
        "wave_id": wave.metadata.get("wave_id"),
        "timestamp": wave.timestamp,
        "policy": policy,
        "collapse_result": None,
        "coherence": wave.coherence,
        "origin_trace": wave.origin_trace,
    }

    if policy == "greedy":
        # Deterministically pick peak amplitude
        result["collapse_result"] = {
            "phase": wave.phase,
            "amplitude": wave.amplitude,
        }

    elif policy == "probabilistic":
        # Collapse stochastically using amplitude² as weight
        chance = wave.amplitude ** 2
        if random.random() < min(chance, 1.0):
            result["collapse_result"] = {
                "phase": wave.phase,
                "amplitude": wave.amplitude,
            }
        else:
            result["collapse_result"] = None  # Collapse failed or null event

    elif policy == "selective":
        # Use selector dict to check for match (e.g. origin, coherence threshold)
        if selector:
            coherence_ok = wave.coherence >= selector.get("min_coherence", 0.0)
            origin_match = selector.get("origin") in wave.origin_trace if selector.get("origin") else True
            if coherence_ok and origin_match:
                result["collapse_result"] = {
                    "phase": wave.phase,
                    "amplitude": wave.amplitude,
                }
            else:
                result["collapse_result"] = None
        else:
            result["collapse_result"] = None

    else:
        raise ValueError(f"Unknown measurement policy: {policy}")

    return result