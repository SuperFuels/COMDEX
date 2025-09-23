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
    """A Symatics wave state (continuous field)."""
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

    def emit_photon(self, glyph: Optional[str] = None) -> "Photon":
        """
        Emit a photon as a discrete symbolic packet from this wave.
        Non-destructive: the wave continues to exist after emission.
        Symmetric API to Photon.from_wave().
        """
        return Photon.from_wave(self, glyph=glyph)


# ----------------------------
# 💡 Photon Primitive
# ----------------------------

@dataclass
class Photon:
    """A photon as an indivisible carrier of symbolic wave information (discrete quantum).

    Typically emitted from a Wave collapse or interaction event.
    Serves as the discrete token bridging continuous waves ↔ symbolic Codex glyphs.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    wavelength: float = 500e-9  # meters (λ = c / f)
    polarization: str = "linear"
    glyph: Optional[str] = None  # symbolic glyph association (⊕, ↔, etc.)
    energy: Optional[float] = None  # Joules (E = h f)
    source_wave: Optional[str] = None  # lineage link back to originating wave

    def signature(self) -> str:
        """Return symbolic photon signature string."""
        return f"💡[{self.wavelength*1e9:.1f}nm, pol={self.polarization}, glyph={self.glyph}]"

    @classmethod
    def from_wave(cls, wave: Wave, glyph: Optional[str] = None) -> "Photon":
        """
        Construct a photon directly from a wave (dual to Wave.emit_photon()).
        Uses λ = c / f and E = h f.
        """
        c = 3e8  # m/s
        h = 6.626e-34  # J·s
        wavelength = c / wave.frequency if wave.frequency > 0 else float("inf")
        energy = h * wave.frequency
        return cls(
            wavelength=wavelength,
            polarization=wave.polarization,
            glyph=glyph,
            energy=energy,
            source_wave=wave.id,
        )

# ----------------------------
# ⊕ ↔ ⟲ ∇ ⇒ Operators
# ----------------------------

def superpose(w1: Wave, w2: Wave) -> Wave:
    """⊕ Superposition: combine two waves into a new interference pattern."""
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
    """↔ Entanglement: return a bound symbolic state of two waves."""
    return {
        "op": "↔",
        "state": f"{w1.id} ↔ {w2.id}",
        "non_local": True,
        "metadata": {"freqs": (w1.frequency, w2.frequency)}
    }


def resonate(w: Wave, cycles: int = 1) -> Wave:
    """⟲ Resonance: reinforce or decay a wave depending on natural frequency match."""
    factor = 1.0 + 0.1 * cycles
    return Wave(
        frequency=w.frequency,
        amplitude=w.amplitude * factor,
        phase=w.phase,
        polarization=w.polarization,
        metadata={"op": "⟲", "cycles": cycles, "parent": w.id}
    )


def collapse(w: Wave, emit: bool = False, glyph: Optional[str] = None):
    """
    ∇ Collapse: reduce wave to a measurable symbolic signature.
    Optionally emit a Photon representing the discrete measurement event.
    """
    signature = {
        "op": "∇",
        "wave_id": w.id,
        "signature": w.signature(),
        "collapsed_value": round(w.frequency, 2),
    }

    if emit:
        photon = w.emit_photon(glyph=glyph)
        return signature, photon

    return signature


def trigger(glyph: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """⇒ Trigger: glyph execution primitive (Qwave beams, CodexCore hooks)."""
    return {"op": "⇒", "glyph": glyph, "payload": payload or {}}


# ----------------------------
# ⊗ ≡ ⇌ ⋈ ⟡ New Operators
# ----------------------------

def tensorize(w1: Wave, w2: Wave) -> Wave:
    """⊗ Tensor Product: compose two waves into a coupled higher-order state."""
    return Wave(
        frequency=w1.frequency * w2.frequency,
        amplitude=w1.amplitude * w2.amplitude,
        phase=(w1.phase + w2.phase) % (2 * math.pi),
        polarization=f"{w1.polarization}-{w2.polarization}",
        metadata={"op": "⊗", "parents": [w1.id, w2.id]}
    )


def equivalent(w1: Wave, w2: Wave) -> Dict[str, Any]:
    """≡ Equivalence: check symbolic alignment between two waves."""
    return {
        "op": "≡",
        "equivalent": math.isclose(w1.frequency, w2.frequency, rel_tol=1e-3),
        "delta_freq": abs(w1.frequency - w2.frequency),
        "waves": (w1.id, w2.id),
    }


def reversible(w: Wave) -> Wave:
    """⇌ Reversibility: invert the phase of a wave (time reversal symmetry)."""
    return Wave(
        frequency=w.frequency,
        amplitude=w.amplitude,
        phase=(-w.phase) % (2 * math.pi),
        polarization=w.polarization,
        metadata={"op": "⇌", "parent": w.id}
    )


def fuse(w1: Wave, w2: Wave) -> Wave:
    """⋈ Fusion: merge two waves into a single stabilized form."""
    return Wave(
        frequency=(w1.frequency + w2.frequency) / 2,
        amplitude=math.sqrt(w1.amplitude**2 + w2.amplitude**2),
        phase=(w1.phase + w2.phase) / 2,
        polarization="mixed",
        metadata={"op": "⋈", "parents": [w1.id, w2.id]}
    )


def crystallize(w: Wave) -> Dict[str, Any]:
    """⟡ Crystallization: freeze wave into a symbolic lattice snapshot."""
    return {
        "op": "⟡",
        "wave_id": w.id,
        "lattice_signature": hash((w.frequency, w.amplitude, w.phase, w.polarization)),
        "frozen": True,
    }


# ----------------------------
# Example Demo
# ----------------------------

def demo_all(print_out: bool = True) -> Dict[str, Any]:
    """Run a full demo of Symatics primitives and operators.

    Args:
        print_out: If True, also print results to stdout (for interactive demo).
    Returns:
        Dict of results keyed by operation name for programmatic use.
    """
    w1 = Wave(frequency=440.0, amplitude=1.0, phase=0.0, polarization="linear")
    w2 = Wave(frequency=442.0, amplitude=0.8, phase=0.1, polarization="circular")

    results: Dict[str, Any] = {}

    results["wave1"] = w1.signature()
    results["wave2"] = w2.signature()

    results["superposed"] = superpose(w1, w2).signature()
    results["entangled"] = entangle(w1, w2)
    results["resonated"] = resonate(w1, cycles=3).signature()
    results["collapsed"] = collapse(w2)
    results["trigger"] = trigger("⊕", {"action": "add"})

    # Extended operators
    results["tensorized"] = tensorize(w1, w2).signature()
    results["equivalent"] = equivalent(w1, w2)
    results["reversible"] = reversible(w1).signature()
    results["fused"] = fuse(w1, w2).signature()
    results["crystallized"] = crystallize(w1)

    # Photon bridge
    results["photon_emit"] = w1.emit_photon("⊕").signature()
    results["photon_from_wave"] = Photon.from_wave(w2, "↔").signature()
    collapsed_sig, photon3 = collapse(w2, emit=True, glyph="⊕")
    results["collapsed_emit"] = {"signature": collapsed_sig, "photon": photon3.signature()}

    if print_out:
        for k, v in results.items():
            print(f"{k}: {v}")

    return results


if __name__ == "__main__":
    demo_all(print_out=True)


# Explicit exports for clean imports
__all__ = [
    "Wave",
    "Photon",
    "superpose",
    "entangle",
    "resonate",
    "collapse",
    "trigger",
    "tensorize",
    "equivalent",
    "reversible",
    "fuse",
    "crystallize",
    "demo_all",
]