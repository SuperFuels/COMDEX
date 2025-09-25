from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import math
from .signature import Signature

@dataclass
class Wave:
    """Concrete wave carrier; used to derive signatures."""
    amplitude: float
    frequency: float
    phase: float
    polarization: str
    mode: Optional[str] = None
    oam_l: Optional[int] = None
    envelope: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def signature(self) -> Signature:
        return Signature(
            amplitude=self.amplitude,
            frequency=self.frequency,
            phase=self.phase,
            polarization=self.polarization,
            mode=self.mode,
            oam_l=self.oam_l,
            envelope=self.envelope,
            meta=self.meta
        )

    # ---------------------------
    # Semantic operations (v0.1)
    # ---------------------------

    def fuse(self, other: "Wave", phi: float = 0.0) -> "Wave":
        """
        ⋈ Fusion/Interference: merge two waves with a phase offset φ.
        Uses phasor addition in complex plane.
        """
        z1 = self.amplitude * math.e**(1j * self.phase)
        z2 = other.amplitude * math.e**(1j * (other.phase + phi))
        z = z1 + z2
        A, ph = abs(z), math.atan2(z.imag, z.real)
        return Wave(
            amplitude=A,
            frequency=(self.frequency + other.frequency) / 2,
            phase=ph % (2 * math.pi),
            polarization="mixed",
            meta={"op": "⋈", "phi": phi, "parents": [id(self), id(other)]}
        )

    def resonate(self, other: "Wave") -> "Wave":
        """
        ⟲ Resonance: amplify if nearly matched, else soft select.
        """
        df = abs(self.frequency - other.frequency)
        if df < 1e-6:
            amp = max(self.amplitude, other.amplitude) * 1.25
            phase = (self.phase + other.phase) / 2.0
            return Wave(
                amplitude=amp,
                frequency=(self.frequency + other.frequency) / 2.0,
                phase=phase,
                polarization="mixed",
                meta={"op": "⟲", "resonant": True, "df": df}
            )
        pick = self if self.amplitude >= other.amplitude else other
        return Wave(
            amplitude=pick.amplitude * 0.98,
            frequency=pick.frequency,
            phase=pick.phase,
            polarization=pick.polarization,
            meta={"op": "⟲", "resonant": False, "df": df}
        )

    def damp(self, gamma: float, steps: int = 1) -> "Wave":
        """
        ↯ Damping: exponential decay of amplitude.
        """
        A = self.amplitude * math.exp(-gamma * steps)
        return Wave(
            amplitude=A,
            frequency=self.frequency,
            phase=self.phase,
            polarization=self.polarization,
            meta={"op": "↯", "gamma": gamma, "steps": steps}
        )


SignatureVector = list[Signature]

def canonical_signature(sig: Signature) -> Signature:
    """
    Canonicalization used by measurement μ(·).
    Round/tie-break to nearest stable lattice point in signature space.
    """
    fppm = 1e-6
    f = (
        round(sig.frequency / (sig.frequency * fppm)) * (sig.frequency * fppm)
        if sig.frequency else 0.0
    )
    ph = sig.phase % (2 * math.pi)
    return Signature(
        amplitude=sig.amplitude,
        frequency=f,
        phase=ph,
        polarization=sig.polarization,
        mode=sig.mode,
        oam_l=sig.oam_l,
        envelope=sig.envelope,
        meta=sig.meta,
    )