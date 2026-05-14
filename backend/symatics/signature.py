from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional

@dataclass(frozen=True)
class Domain:
    name: str

@dataclass(frozen=True)
class Property:
    name: str
    value: Any

@dataclass(frozen=True)
class Signature:
    """
    A machine-tractable 'unit' of Symatics: stable invariants of a wave/glyph.
    """
    amplitude: float
    frequency: float
    phase: float
    polarization: str   # e.g., "H","V","RHC","LHC"
    mode: Optional[str] = None  # e.g., "LG01", "TEM00"
    oam_l: Optional[int] = None
    envelope: Optional[str] = None  # "gaussian","rect","chirp"
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Equivalence:
    """Tolerance-based equivalence on signatures."""
    amp_eps: float = 1e-3
    freq_eps: float = 1e-6
    phase_eps: float = 1e-3

    def equal(self, a: Signature, b: Signature) -> bool:
        if abs(a.amplitude - b.amplitude) > self.amp_eps: return False
        if abs(a.frequency - b.frequency) > self.freq_eps: return False
        # phase modulo 2π
        pdiff = (a.phase - b.phase) % (2.0*3.141592653589793)
        if min(pdiff, 2.0*3.141592653589793 - pdiff) > self.phase_eps: return False
        if a.polarization != b.polarization: return False
        if a.mode != b.mode: return False
        if a.oam_l != b.oam_l: return False
        return True