"""
Tessaris • Quantum Quad Core (QQC)
Symatics Lightwave Engine (SLE) — Core Bridge Package

This package forms the Symbolic ↔ Photonic interface layer.
It handles:
 - Dispatching symbolic instructions (⊕ μ ↔ ⟲ π)
 - Wrapping them into photonic WaveCapsules
 - Executing via the BeamRuntime (photonic kernel)
"""

from .symatics_dispatcher import SymaticsDispatcher
from .wave_capsule import WaveCapsule
from .beam_runtime import BeamRuntime

__all__ = ["SymaticsDispatcher", "WaveCapsule", "BeamRuntime"]