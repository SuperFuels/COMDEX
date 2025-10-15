# -*- coding: utf-8 -*-
"""
Riemann Photonic Driver – bridges symbolic primes to the QWave/SLE stack.
"""

import numpy as np
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.kernels.interference_kernel_core import join_waves_batch


def build_prime_waves(primes, sigma=0.5):
    """
    Create synthetic WaveState objects corresponding to prime frequency modes.
    These mimic photon superpositions in the Tessaris ⊕ domain.
    """
    waves = []
    for p in primes:
        amp = p ** (-sigma)
        phase = np.log(p)
        w = WaveState(
            glyph_id=f"p{p}",
            glyph_data={"prime": p},
            carrier_type="prime_mode",
            modulation_strategy="riemann",
            metadata={"carrier_type": "prime_mode"},
        )
        # assign photonic attributes directly (not in constructor)
        w.amplitude = amp
        w.phase = phase
        w.coherence = 1.0
        waves.append(w)
    return waves


def photonic_resonance_curve(t_grid, sigma=0.5, pmax=5000, phase_scale=30.0):
    """
    Uses Tessaris ⊕ kernel (join_waves_batch) to build R(t) photonic-style.
    Compatible with join_waves_batch returning either dict or WaveState.
    """
    from backend.tests.test_riemann_probe import primes_upto

    ps = primes_upto(pmax)
    R = []

    for t in t_grid:
        waves = build_prime_waves(ps, sigma)
        # apply phase evolution
        for w in waves:
            w.phase = w.phase * (t * phase_scale)

        result = join_waves_batch(waves)

        # Depending on kernel output type
        if isinstance(result, dict):
            amp = result.get("combined_amplitude") or result.get("amplitude") or 0.0
        elif hasattr(result, "amplitude"):
            amp = getattr(result, "amplitude", 0.0)
        elif hasattr(result, "metadata") and "collapse_metrics" in result.metadata:
            amp = result.metadata.get("collapse_metrics", {}).get("intensity", 0.0)
        else:
            amp = sum(getattr(x, "amplitude", 0.0) for x in waves)

        R.append(abs(amp))

    R = np.array(R)
    R /= (R.max() + 1e-12)
    return R