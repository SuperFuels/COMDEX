# backend/symatics/photon.py
# ---------------------------------------------------------------------
# Photon: discrete quanta of the Wave field
# - Complements wave.py (continuous carrier)
# - Supports energy, spin/helicity, entanglement, and Codex signatures
# ---------------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
from .signature import Signature

# Planck constant [J·s]
PLANCK_H = 6.62607015e-34


@dataclass
class Photon:
    """Discrete photon carrier; quantum excitation of a Wave."""
    frequency: float                   # Hz
    polarization: str                  # e.g. "H", "V", "L", "R"
    helicity: Optional[int] = None     # ±1 for spin states
    entangled_id: Optional[str] = None # entanglement partner/group ID
    meta: Optional[Dict[str, Any]] = None

    @property
    def energy(self) -> float:
        """Photon energy [J] via E = h * f."""
        return PLANCK_H * self.frequency

    def signature(self) -> Signature:
        """
        Build a symbolic Signature (Codex-level).
        Amplitude defaults to 1.0 for a single photon.
        Phase is not meaningful for a single photon, so set 0.0.
        """
        return Signature(
            amplitude=1.0,
            frequency=self.frequency,
            phase=0.0,
            polarization=self.polarization,
            mode=None,
            oam_l=None,
            envelope=None,
            meta=self.meta
        )


# ----------------------------
# Utility functions
# ----------------------------
def photons_from_wave(wave: "Wave", count: int = 1) -> list[Photon]:
    """
    Convert a continuous Wave into N photons with same frequency/polarization.
    Phase/envelope are ignored at single-photon granularity.
    """
    from .wave import Wave  # local import to avoid circular dependency
    return [
        Photon(
            frequency=wave.frequency,
            polarization=wave.polarization,
            helicity=None,
            entangled_id=None,
            meta={"derived_from": "Wave", **(wave.meta or {})},
        )
        for _ in range(count)
    ]


def entangle_photons(p1: Photon, p2: Photon, group_id: Optional[str] = None) -> tuple[Photon, Photon]:
    """
    Tag two photons as entangled by setting a shared entangled_id.
    Returns updated photon pair.
    """
    gid = group_id or f"ent_{id(p1)}_{id(p2)}"
    p1.entangled_id = gid
    p2.entangled_id = gid
    return p1, p2


# Public API
__all__ = [
    "Photon",
    "photons_from_wave",
    "entangle_photons",
]