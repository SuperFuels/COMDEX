from __future__ import annotations
"""
───────────────────────────────────────────────────────────────
Tessaris RQC - Photonic Propagation Simulator
───────────────────────────────────────────────────────────────
Simulates symbolic wave propagation and coherence evolution
using the symbol->wave encodings from GlyphNetPhaseMap.

Supports both:
  * Linear propagation (open) - for ⊕, ↔ operations.
  * Resonant loopback (closed) - for ⟲, πs phase-closure testing.

Outputs:
  * Phase error evolution
  * Coherence (|⟨e^{i(φ_i-φ_j)}⟩|)
  * Closure stability index
  * Energy-information trace

This module forms the dynamic substrate of the Tessaris
Resonance Quantum Computer (RQC) photonic runtime.
───────────────────────────────────────────────────────────────
"""

# ──────────────────────────────────────────────
#  Tessaris Path Bootstrapping
#  (ensures module can be run directly or via -m)
# ──────────────────────────────────────────────
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# ──────────────────────────────────────────────
#  Imports
# ──────────────────────────────────────────────

import numpy as np
import math
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple

from photon_runtime.encodings.glyphnet_phase_map import GLYPHNET_PHASE_MAP, WaveDescriptor


@dataclass
class PropagationResult:
    time: np.ndarray
    field: np.ndarray
    coherence: np.ndarray
    phase_error: np.ndarray
    closure_index: np.ndarray


class PropagationSimulator:
    """
    Simulates symbolic wave evolution across timesteps.
    This forms the physical substrate for ⊕, ⟲, ↔, μ operators.
    """

    def __init__(self, dt: float = 1e-3, steps: int = 10000) -> None:
        self.dt = dt
        self.steps = steps
        self.time = np.linspace(0, steps * dt, steps)

    # -------------------------------------------------------------
    def propagate(
        self,
        symbols: List[str],
        loopback: bool = True,
        damping: float = 0.0005,
        noise: float = 0.0001,
    ) -> PropagationResult:
        """Propagate a list of registered symbols through time."""
        waves = [GLYPHNET_PHASE_MAP.get(s) for s in symbols]
        n = len(waves)

        field = np.zeros(self.steps, dtype=np.complex128)
        coherence = np.zeros(self.steps)
        phase_error = np.zeros(self.steps)
        closure_index = np.zeros(self.steps)

        for t_idx, t in enumerate(self.time):
            # Construct instantaneous field sum
            psi_t = sum(
                w.amplitude
                * np.exp(1j * (2 * np.pi * w.frequency * t + w.phase))
                for w in waves
            )
            field[t_idx] = psi_t

            # Compute coherence between all pairs
            phi_values = [2 * np.pi * w.frequency * t + w.phase for w in waves]
            diffs = [math.cos(phi_i - phi_j) for phi_i in phi_values for phi_j in phi_values]
            coherence[t_idx] = abs(np.mean(diffs))

            # Closure check: phase difference modulo 2π
            phase_error[t_idx] = np.std(phi_values)
            closure_index[t_idx] = 1.0 - (phase_error[t_idx] / (2 * np.pi))

            # Loopback feedback (⟲)
            if loopback:
                for w in waves:
                    # Gradual phase correction towards closure
                    w.phase -= damping * (phase_error[t_idx]) + np.random.randn() * noise

        return PropagationResult(
            time=self.time,
            field=field,
            coherence=coherence,
            phase_error=phase_error,
            closure_index=closure_index,
        )

    # -------------------------------------------------------------
    @staticmethod
    def summarize(result: PropagationResult) -> Dict[str, Any]:
        """Return summary metrics from a PropagationResult."""
        return {
            "mean_coherence": float(np.mean(result.coherence)),
            "final_coherence": float(result.coherence[-1]),
            "min_phase_error": float(np.min(result.phase_error)),
            "closure_stability": float(np.mean(result.closure_index)),
        }


# Example usage ----------------------------------------------------
if __name__ == "__main__":
    sim = PropagationSimulator(dt=1e-3, steps=2000)
    result = sim.propagate(["⊕", "μ", "⟲", "↔"], loopback=True)

    summary = PropagationSimulator.summarize(result)
    print("\n--- RQC Propagation Summary ---")
    for k, v in summary.items():
        print(f"{k:20s}: {v:.5f}")