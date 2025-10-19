# ===============================
# 📁 backend/quant/qtensor/qtensor_field.py
# ===============================
"""
🧩 QTensorField — Tensorized Wave Algebra Core
----------------------------------------------
Extends QMathWaveOps to vector/tensor domains.

Implements element-wise and broadcastable operations
for wave arrays representing fields of Φ/ψ amplitudes.

Dependencies: NumPy (for CPU tensor math).  Safe to
swap with JAX or CuPy later in QQC backend.
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Any, Tuple

from backend.quant.qmath.qmath_waveops import (
    superpose,
    entangle,
    resonate,
    collapse,
    measure,
)

# ----------------------------------------------------------------------
# QTensorField class
# ----------------------------------------------------------------------
class QTensorField:
    """
    Represents an N-D tensor of complex wave amplitudes.

    Attributes:
        data: np.ndarray[complex]
        meta: optional info (shape, phase basis, etc.)
    """

    def __init__(self, data: np.ndarray, meta: Dict[str, Any] | None = None):
        self.data = np.asarray(data, dtype=np.complex128)
        self.meta = meta or {}
        self.meta.setdefault("shape", self.data.shape)
        self.meta.setdefault("dtype", str(self.data.dtype))

    # ------------------------------------------------------------------
    def superpose(self, other: "QTensorField", weight: float = 0.5) -> "QTensorField":
        """Element-wise ⊕ superposition."""
        res = weight * self.data + (1.0 - weight) * other.data
        return QTensorField(res, {"op": "⊕", "weight": weight})

    # ------------------------------------------------------------------
    def entangle(self, other: "QTensorField") -> Tuple["QTensorField", "QTensorField", float]:
        """Element-wise ↔ entanglement with mean correlation ρ."""
        a = self.data
        b = other.data
        corr = np.real(a.conj() * b)
        ρ = float(np.clip(np.mean(np.abs(corr)), 0.0, 1.0))
        phase_avg = np.angle(a) / 2 + np.angle(b) / 2
        shift = np.exp(1j * phase_avg)
        a2, b2 = a * shift, b * shift
        return QTensorField(a2), QTensorField(b2), ρ

    # ------------------------------------------------------------------
    def resonate(self, feedback: float = 0.1, damping: float = 0.95, steps: int = 5) -> "QTensorField":
        """Iterative ⟲ resonance across all elements."""
        ψ = self.data.copy()
        for _ in range(steps):
            ψ = (1 + feedback) * ψ * damping
        return QTensorField(ψ, {"op": "⟲", "feedback": feedback, "damping": damping})

    # ------------------------------------------------------------------
    def collapse(self) -> np.ndarray:
        """∇ collapse → measurable intensity field (|ψ|²)."""
        return np.abs(self.data) ** 2

    # ------------------------------------------------------------------
    def measure(self) -> Dict[str, Any]:
        """μ measurement → amplitude / phase / intensity stats."""
        amp = np.abs(self.data)
        phase = np.angle(self.data)
        return {
            "amplitude_mean": float(np.mean(amp)),
            "phase_mean": float(np.mean(phase)),
            "intensity_mean": float(np.mean(amp ** 2)),
            "amplitude_var": float(np.var(amp)),
            "phase_var": float(np.var(phase)),
        }

    # ------------------------------------------------------------------
    def interact(self, other: "QTensorField") -> Dict[str, Any]:
        """Composite interaction pipeline (⊕ → ↔ → ⟲ → ∇ → μ)."""
        s = self.superpose(other)
        ea, eb, ρ = s.entangle(other)
        r = ea.resonate()
        I = r.collapse()
        μ = r.measure()
        return {
            "superposed": s,
            "entangled_a": ea,
            "entangled_b": eb,
            "correlation": ρ,
            "resonant": r,
            "intensity_field": I,
            "measurement": μ,
        }

    # ------------------------------------------------------------------
    def normalize(self) -> "QTensorField":
        """Normalize total intensity to 1.0."""
        norm = np.linalg.norm(self.data)
        if norm == 0:
            return self
        return QTensorField(self.data / norm, {"op": "normalize"})

    # ------------------------------------------------------------------
    def __repr__(self):
        shp = "×".join(map(str, self.data.shape))
        return f"QTensorField(shape={shp}, mean|ψ|={np.mean(np.abs(self.data)):.3f})"


# ----------------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------------
def random_field(shape: Tuple[int, ...], phase_spread: float = np.pi) -> QTensorField:
    """
    Generate a random complex field with uniform phase distribution.
    """
    amp = np.random.rand(*shape)
    phase = np.random.uniform(-phase_spread, phase_spread, size=shape)
    data = amp * np.exp(1j * phase)
    return QTensorField(data, {"generated": True})


# ----------------------------------------------------------------------
# Self-test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    a = random_field((4, 4))
    b = random_field((4, 4))
    result = a.interact(b)
    print("ρ =", result["correlation"])
    print("μ =", result["measurement"])