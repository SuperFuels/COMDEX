"""
Symatics Primitives
-------------------
Core building blocks of the Symatics Algebra system.

These are the "atoms" of Symatics: waves, photons, and symbolic operators.
They serve as the foundation for axioms, algebraic laws, and higher-level calculus.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import uuid
import math
import cmath
import random


# ----------------------------
# 🌊 Wave Primitive
# ----------------------------

@dataclass
class Wave:
    """A Symatics wave state."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    frequency: float = 1.0     # Hz
    amplitude: float = 1.0     # Arbitrary unit
    phase: float = 0.0         # Radians
    polarization: str = "linear"  # "linear", "circular", etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def signature(self) -> str:
        """Generate a symbolic signature string for this wave."""
        return f"🌊[{self.frequency:.2f}Hz, {self.amplitude:.2f}A, {self.phase:.2f}rad, {self.polarization}]"

    def complex_form(self, t: float = 0.0) -> complex:
        """Return the complex wave representation at time t."""
        return self.amplitude * cmath.exp(1j * (2 * math.pi * self.frequency * t + self.phase))


# ----------------------------
# 💡 Photon Primitive
# ----------------------------

@dataclass
class Photon:
    """A photon as an indivisible carrier of symbolic wave information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    wavelength: float = 500e-9  # meters
    polarization: str = "linear"
    glyph: Optional[str] = None  # symbolic glyph association (⊕, ↔, etc.)
    energy: Optional[float] = None  # optional, J

    def signature(self) -> str:
        """Return symbolic photon signature."""
        return f"💡[{self.wavelength*1e9:.1f}nm, pol={self.polarization}, glyph={self.glyph}]"


# ----------------------------
# ⊕ ↔ ⟲ ∇ ⇒ Operators
# ----------------------------

def superpose(w1: Wave, w2: Wave) -> Wave:
    """
    ⊕ Superposition: combine two waves into a new interference pattern.
    """
    new_amp = (w1.amplitude + w2.amplitude) / 2
    new_phase = (w1.phase + w2.phase) / 2
    new_freq = (w1.frequency + w2.frequency) / 2
    return Wave(
        frequency=new_freq,
        amplitude=new_amp,
        phase=new_phase,
        polarization=random.choice([w1.polarization, w2.polarization]),
        metadata={"op": "⊕", "parents": [w1.id, w2.id]}
    )


def entangle(w1: Wave, w2: Wave) -> Dict[str, Any]:
    """
    ↔ Entanglement: return a bound symbolic state of two waves.
    """
    return {
        "op": "↔",
        "state": f"{w1.id} ↔ {w2.id}",
        "non_local": True,
        "metadata": {"freqs": (w1.frequency, w2.frequency)}
    }


def resonate(w: Wave, cycles: int = 1) -> Wave:
    """
    ⟲ Resonance: reinforce or decay a wave depending on natural frequency match.
    """
    factor = 1.0 + 0.1 * cycles
    return Wave(
        frequency=w.frequency,
        amplitude=w.amplitude * factor,
        phase=w.phase,
        polarization=w.polarization,
        metadata={"op": "⟲", "cycles": cycles, "parent": w.id}
    )


def collapse(w: Wave) -> Dict[str, Any]:
    """
    ∇ Collapse: reduce wave to a measurable symbolic signature.
    """
    signature = {
        "op": "∇",
        "wave_id": w.id,
        "signature": w.signature(),
        "collapsed_value": round(w.frequency, 2)
    }
    return signature


def trigger(glyph: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    ⇒ Trigger: glyph execution primitive (Qwave beams, CodexCore hooks).
    """
    return {
        "op": "⇒",
        "glyph": glyph,
        "payload": payload or {}
    }


# ----------------------------
# Example Demo
# ----------------------------

if __name__ == "__main__":
    w1 = Wave(frequency=440.0, amplitude=1.0, phase=0.0, polarization="linear")
    w2 = Wave(frequency=442.0, amplitude=0.8, phase=0.1, polarization="circular")

    print("Wave 1:", w1.signature())
    print("Wave 2:", w2.signature())

    w3 = superpose(w1, w2)
    print("Superposed:", w3.signature())

    entangled = entangle(w1, w2)
    print("Entangled:", entangled)

    w_res = resonate(w1, cycles=3)
    print("Resonated:", w_res.signature())

    collapsed = collapse(w2)
    print("Collapsed:", collapsed)

    trig = trigger("⊕", {"action": "add"})
    print("Trigger:", trig)