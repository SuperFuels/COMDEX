# symatics/context.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
import math

from .signature import Signature


@dataclass
class Context:
    """
    Symatics execution context (v0.3)
    ---------------------------------
    Holds global parameters for wave/algebra operations to ensure determinism
    and provides runtime evaluation controls for validation and telemetry.
    """

    # --- Core Physical Parameters ------------------------------------------
    lattice_spacing: float = 1e-6          # Frequency lattice spacing (Hz)
    resonance_tolerance: float = 1e-6      # Resonance matching tolerance (Hz)
    polarization_basis: tuple = ("H", "V", "RHC", "LHC")
    noise_floor: float = 1e-12             # Minimum measurable amplitude
    seed: Optional[int] = None             # Collapse RNG seed
    meta: Dict[str, Any] = field(default_factory=dict)

    # --- Optional Canonicalization Hooks -----------------------------------
    _canonicalizer: Optional[Callable[[Signature], Signature]] = None

    # --- Runtime Control Flags (NEW) ---------------------------------------
    validate_runtime: bool = False         # Run LAW_REGISTRY checks
    enable_trace: bool = False             # Emit CodexTrace telemetry
    debug: bool = False                    # Print debug info to stdout

    # -----------------------------------------------------------------------
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
        validate_runtime: bool = False,
        enable_trace: bool = False,
        debug: bool = False,
    ):
        # --- Core config ---
        self.lattice_spacing = lattice_spacing
        self.resonance_tolerance = resonance_tolerance
        self.polarization_basis = polarization_basis
        self.noise_floor = noise_floor
        self.seed = seed
        self.meta = meta or {}

        # --- Canonicalizer / runtime flags ---
        self._canonicalizer = canonicalizer or _canonicalizer
        self.validate_runtime = validate_runtime
        self.enable_trace = enable_trace
        self.debug = debug

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

    # -----------------------------------------------------------------------
    # Logging Utilities
    # -----------------------------------------------------------------------

    def log(self, *args: Any) -> None:
        """Conditional debug logging."""
        if self.debug:
            print("[CTX]", *args)


__all__ = ["Context"]