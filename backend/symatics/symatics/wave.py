from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
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

SignatureVector = list[Signature]

def canonical_signature(sig: Signature) -> Signature:
    """
    Canonicalization used by measurement μ(·).
    Round/tie-break to nearest stable lattice point in signature space.
    """
    # Minimal v0.1 canonicalizer: phase wrap + rounding frequency to ppm grid
    import math
    fppm = 1e-6
    f = round(sig.frequency / (sig.frequency * fppm)) * (sig.frequency * fppm) if sig.frequency else 0.0
    ph = (sig.phase % (2*math.pi))
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