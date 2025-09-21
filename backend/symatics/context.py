# symatics/context.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
import math

from .signature import Signature


@dataclass
class Context:
    """
    Symatics execution context.
    Holds global parameters for wave/algebra operations to ensure determinism.
    Supports both built-in normalization and pluggable canonicalizers.
    """

    # Frequency lattice spacing (Hz)
    lattice_spacing: float = 1e-6

    # Resonance tolerance (Hz)
    resonance_tolerance: float = 1e-6

    # Polarization basis set
    polarization_basis: tuple = ("H", "V", "RHC", "LHC")

    # Noise floor amplitude (minimum measurable value)
    noise_floor: float = 1e-12

    # Collapse randomness seed (optional, for reproducibility)
    seed: Optional[int] = None

    # Metadata / experimental parameters
    meta: Dict[str, Any] = field(default_factory=dict)

    # Optional pluggable canonicalizer (overrides built-in normalization)
    _canonicalizer: Optional[Callable[[Signature], Signature]] = None

    def __init__(
        self,
        lattice_spacing: float = 1e-6,
        resonance_tolerance: float = 1e-6,
        polarization_basis: tuple = ("H", "V", "RHC", "LHC"),
        noise_floor: float = 1e-12,
        seed: Optional[int] = None,
        meta: Optional[Dict[str, Any]] = None,
        canonicalizer: Optional[Callable[[Signature], Signature]] = None,
        _canonicalizer: Optional[Callable[[Signature], Signature]] = None,
    ):
        self.lattice_spacing = lattice_spacing
        self.resonance_tolerance = resonance_tolerance
        self.polarization_basis = polarization_basis
        self.noise_floor = noise_floor
        self.seed = seed
        self.meta = meta or {}
        # accept both canonicalizer and _canonicalizer for convenience
        self._canonicalizer = canonicalizer or _canonicalizer

    # -----------------------------------------------------------------------
    # Built-in normalization rules
    # -----------------------------------------------------------------------

    def normalize_frequency(self, f: float) -> float:
        """Snap frequency to nearest lattice point."""
        return round(f / self.lattice_spacing) * self.lattice_spacing

    def normalize_amplitude(self, a: float) -> float:
        """Clamp amplitude to noise floor."""
        return 0.0 if abs(a) < self.noise_floor else a

    def canonical_phase(self, p: float) -> float:
        """Wrap phase to [0, 2π)."""
        return p % (2 * math.pi)

    # -----------------------------------------------------------------------
    # Canonicalization entrypoint
    # -----------------------------------------------------------------------

    def canonical_signature(self, sig: Signature) -> Signature:
        """
        Apply canonical normalization to a Signature.

        If a custom canonicalizer is provided, delegate to it.
        Otherwise apply default lattice/phase/amplitude normalization.
        """
        if self._canonicalizer:
            return self._canonicalizer(sig)

        return Signature(
            amplitude=self.normalize_amplitude(sig.amplitude),
            frequency=self.normalize_frequency(sig.frequency),
            phase=self.canonical_phase(sig.phase),
            polarization=sig.polarization,
            mode=sig.mode,
            oam_l=sig.oam_l,
            envelope=sig.envelope,
            meta={**sig.meta, "cnf": True},
        )