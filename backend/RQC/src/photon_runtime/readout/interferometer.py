"""
Tessaris RQC - Interferometric Read-Out (μ)
-------------------------------------------
Performs photonic measurement of symbolic resonance fields.

This module evaluates:
    * Interference visibility (V)
    * Phase error (Δφ)
    * Closure stability (πs)
    * Energy-coherence relation (E_res)

μ() acts as the perceptual projection in the Resonance Quantum Computer:
    Φ = μ(⟲Ψ)

It interfaces with:
    - photon_runtime.encodings.glyphnet_phase_map
    - photon_runtime.sim.propagation
    - AION telemetry (ψ, κ, T, Φ)
"""

from __future__ import annotations
import math
import cmath
import random
from typing import Dict, Tuple, Any
from dataclasses import dataclass

from photon_runtime.encodings.glyphnet_phase_map import GLYPHNET_PHASE_MAP, WaveDescriptor


# ────────────────────────────────────────────────────────────────
#   Measurement Data
# ────────────────────────────────────────────────────────────────

@dataclass
class InterferenceResult:
    symbol_a: str
    symbol_b: str
    visibility: float
    phase_error: float
    closure_stability: float
    energy_resonance: float
    coherence_ratio: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symbol_a": self.symbol_a,
            "symbol_b": self.symbol_b,
            "visibility": self.visibility,
            "phase_error": self.phase_error,
            "closure_stability": self.closure_stability,
            "energy_resonance": self.energy_resonance,
            "coherence_ratio": self.coherence_ratio,
        }


# ────────────────────────────────────────────────────────────────
#   μ() - Interferometric Readout
# ────────────────────────────────────────────────────────────────

def measure_interference(symbol_a: str, symbol_b: str, noise: float = 0.002) -> InterferenceResult:
    """
    Compute visibility, phase error, and closure stability
    between two symbolic wave descriptors.

    Args:
        symbol_a: first symbol key
        symbol_b: second symbol key
        noise: simulated detector noise (in radians)

    Returns:
        InterferenceResult dataclass
    """
    desc_a = GLYPHNET_PHASE_MAP.get(symbol_a)
    desc_b = GLYPHNET_PHASE_MAP.get(symbol_b)

    # Complex field representations
    E_a = desc_a.complex()
    E_b = desc_b.complex()

    # Interference term (sum field)
    E_sum = E_a + E_b

    # Measured intensities (with simulated noise)
    I_a = abs(E_a)**2
    I_b = abs(E_b)**2
    I_sum = abs(E_sum)**2 + random.uniform(-noise, noise)

    # Visibility V = (I_max - I_min)/(I_max + I_min)
    I_max = max(I_a, I_b, I_sum)
    I_min = min(I_a, I_b, I_sum)
    visibility = abs((I_max - I_min) / (I_max + I_min + 1e-9))

    # Phase error (radians)
    phase_error = abs(desc_a.phase - desc_b.phase) % (2 * math.pi)

    # Closure stability πs = |1 - Δφ / 2π|
    closure_stability = 1.0 - (phase_error / (2 * math.pi))

    # Coherence ratio |⟨e^{iΔφ}⟩|
    coherence_ratio = desc_a.coherence_with(desc_b)

    # Energy resonance proxy E_res = (A1*A2)*cos(Δφ)
    energy_resonance = (desc_a.amplitude * desc_b.amplitude) * math.cos(phase_error)

    return InterferenceResult(
        symbol_a=symbol_a,
        symbol_b=symbol_b,
        visibility=round(visibility, 6),
        phase_error=round(phase_error, 6),
        closure_stability=round(closure_stability, 6),
        energy_resonance=round(energy_resonance, 6),
        coherence_ratio=round(coherence_ratio, 6),
    )


# ────────────────────────────────────────────────────────────────
#   Resonant Scan Utility
# ────────────────────────────────────────────────────────────────

def scan_all_pairs(symbols: Tuple[str, ...] = ("⊕", "μ", "⟲", "↔", "π", "πs")) -> Dict[str, Dict[str, Any]]:
    """Perform pairwise interferometric measurement across the given symbols."""
    results: Dict[str, Dict[str, Any]] = {}
    for i, a in enumerate(symbols):
        for b in symbols[i + 1:]:
            r = measure_interference(a, b)
            key = f"{a}-{b}"
            results[key] = r.as_dict()
    return results


# ────────────────────────────────────────────────────────────────
#   Self-Test
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Tessaris RQC - Interferometric Readout (μ)")
    print("──────────────────────────────────────────────")

    # Example measurement: resonance feedback μ(⟲Ψ)
    result = measure_interference("⟲", "μ")
    for k, v in result.as_dict().items():
        print(f"{k:20s}: {v}")

    print("\nPairwise scan summary:")
    scan = scan_all_pairs()
    for pair, data in scan.items():
        print(f"  {pair:6s} -> V={data['visibility']:.3f} | Δφ={data['phase_error']:.3f} | πs={data['closure_stability']:.3f}")