"""
Tessaris RQC - Symbol->Wave Encoding Map (v0.4)
----------------------------------------------

Maps Symatic operators and meta-symbols to phase-amplitude wave descriptors
for use in the Resonance Quantum Computer photonic runtime.

Each symbol corresponds to a resonant field with:
    * amplitude  (A)
    * phase       (φ)
    * frequency   (f)
    * polarization (P)

The encodings below form the "resonance alphabet" - the symbolic modes that
propagate through the photonic simulation (propagation.py), feed telemetry (AION),
and couple via QQC harmonic cores.

Updated for Symatics v0.4 / AION integration:
    - Includes ψ-κ-T-Φ base fields
    - Adds dynamic coherence weighting
    - Introduces harmonic mode families for QQC subcores
"""

from __future__ import annotations
import math
import cmath
import random
from dataclasses import dataclass, field
from typing import Dict, Any


# ────────────────────────────────────────────────────────────────
#   WaveDescriptor
# ────────────────────────────────────────────────────────────────

@dataclass
class WaveDescriptor:
    symbol: str
    amplitude: float
    phase: float
    frequency: float
    polarization: str = "linear"
    coherence_weight: float = 1.0  # relative stability factor (for AION tuning)

    def complex(self) -> complex:
        """Return complex representation A*e^{iφ}."""
        return self.amplitude * cmath.exp(1j * self.phase)

    def coherence_with(self, other: "WaveDescriptor") -> float:
        """Return normalized coherence magnitude |⟨e^{i(φ_i-φ_j)}⟩| weighted by stability."""
        phase_diff = self.phase - other.phase
        base = abs(cmath.exp(1j * phase_diff))
        return base * ((self.coherence_weight + other.coherence_weight) / 2.0)


# ────────────────────────────────────────────────────────────────
#   GlyphNetPhaseMap
# ────────────────────────────────────────────────────────────────

class GlyphNetPhaseMap:
    """Symbol->wave encoding registry for Tessaris RQC."""

    def __init__(self) -> None:
        self._registry: Dict[str, WaveDescriptor] = {}
        self._init_default_encodings()

    # -------------------------------------------------------------
    def _init_default_encodings(self) -> None:
        """Default encodings for Symatic operators and AION base fields."""
        base = 1.0
        ω = 1.0  # base frequency (normalized harmonic)

        # Core Symatic Operators - symbolic -> photonic encoding
        self.register_symbol("⊕",  amplitude=base, phase=0.0,          frequency=ω)
        self.register_symbol("μ",  amplitude=base, phase=math.pi/4,    frequency=ω)
        self.register_symbol("⟲",  amplitude=base, phase=math.pi/2,    frequency=ω)
        self.register_symbol("↔",  amplitude=base, phase=3*math.pi/4,  frequency=ω)
        self.register_symbol("π",  amplitude=base, phase=math.pi,      frequency=ω)
        self.register_symbol("πs", amplitude=base, phase=2*math.pi,    frequency=ω)

        # AION Cognitive Field Components
        self.register_symbol("ψ", amplitude=0.95, phase=0.0,            frequency=ω*0.95, coherence_weight=1.0)
        self.register_symbol("κ", amplitude=0.85, phase=math.pi/3,      frequency=ω*1.05, coherence_weight=0.9)
        self.register_symbol("T", amplitude=1.00, phase=2*math.pi/3,    frequency=ω*1.10, coherence_weight=0.92)
        self.register_symbol("Φ", amplitude=1.10, phase=math.pi,        frequency=ω*1.15, coherence_weight=0.95)

        # QQC Harmonic Subcore Phase Offsets
        for i, sub in enumerate(["A", "B", "C", "D"], start=0):
            self.register_symbol(
                f"QQC{sub}",
                amplitude=1.0,
                phase=(i * math.pi / 2),
                frequency=ω * (1.0 + 0.02 * i),
                polarization="circular" if i % 2 else "linear",
                coherence_weight=0.98
            )

    # -------------------------------------------------------------
    def register_symbol(self, symbol: str, **params: Any) -> None:
        """Register or update a symbol encoding."""
        desc = WaveDescriptor(symbol=symbol, **params)
        self._registry[symbol] = desc

    def get(self, symbol: str) -> WaveDescriptor:
        """Retrieve descriptor for a symbol."""
        if symbol not in self._registry:
            raise KeyError(f"Symbol '{symbol}' not registered in phase map.")
        return self._registry[symbol]

    # -------------------------------------------------------------
    def delta_phi(self, a: str, b: str) -> float:
        """Return phase difference between two registered symbols (radians)."""
        return self.get(a).phase - self.get(b).phase

    def coherence(self, a: str, b: str) -> float:
        """Return coherence magnitude between two symbols."""
        return self.get(a).coherence_with(self.get(b))

    # -------------------------------------------------------------
    def dynamic_tune(self, noise_level: float = 0.01) -> None:
        """
        Apply small stochastic phase jitter to simulate environmental noise
        and re-normalize coherence weights (used by AION adaptive tuning loop).
        """
        for desc in self._registry.values():
            jitter = random.uniform(-noise_level, noise_level)
            desc.phase = (desc.phase + jitter) % (2 * math.pi)
            desc.coherence_weight = max(0.0, min(1.0, desc.coherence_weight - abs(jitter)*5))

    def summary(self) -> Dict[str, Dict[str, Any]]:
        """Return dict summary of all registered encodings."""
        return {
            s: {
                "amplitude": round(d.amplitude, 4),
                "phase": round(d.phase, 4),
                "frequency": round(d.frequency, 4),
                "polarization": d.polarization,
                "coherence_weight": round(d.coherence_weight, 3),
            }
            for s, d in self._registry.items()
        }


# ────────────────────────────────────────────────────────────────
#   Global Map Singleton
# ────────────────────────────────────────────────────────────────

GLYPHNET_PHASE_MAP = GlyphNetPhaseMap()


# ────────────────────────────────────────────────────────────────
#   Self-Test
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    m = GlyphNetPhaseMap()
    print("Default coherence(⊕,⟲):", round(m.coherence("⊕", "⟲"), 4))
    print("Phase difference (ψ,Φ):", round(m.delta_phi("ψ", "Φ"), 4))
    print("Summary snapshot:")
    for k, v in m.summary().items():
        print(f"  {k}: {v}")