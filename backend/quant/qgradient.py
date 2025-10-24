# ================================================================
# 💠 QuantPy Gradient & Collapse Operator (∇ψ)
# ================================================================
"""
Implements the ∇ψ operator for QuantPy wave/tensor fields.
Used to compute gradient-based resonance flow and collapse metrics.

Integrates with:
    backend.quant.qtensor.qtensor_field.QTensorField
    backend.quant.qmath.qmath_waveops
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Any
from backend.quant.qtensor.qtensor_field import QTensorField


# ------------------------------------------------------------
# ∇ψ — Gradient Operator
# ------------------------------------------------------------
def gradient(field: QTensorField) -> QTensorField:
    """
    Compute ∇ψ (gradient) for a QTensorField.
    Produces a complex-valued tensor representing directional flow of ψ.
    """
    ψ = field.data
    grad_components = np.gradient(ψ)
    grad_sum = np.zeros_like(ψ, dtype=np.complex128)
    for g in grad_components:
        grad_sum += g

    meta = field.meta.copy()
    meta.update({"op": "∇", "description": "gradient of ψ"})
    return QTensorField(grad_sum, meta)


# ------------------------------------------------------------
# ∇ collapse — Gradient Collapse & Resonance Sync
# ------------------------------------------------------------
def collapse_gradient(field: QTensorField) -> Dict[str, Any]:
    """
    Compute intensity |ψ|², gradient field ∇ψ, and coherence summary.
    Returns dict with collapsed intensity, gradient magnitude, and phase stats.
    """
    ψ = field.data
    intensity = np.abs(ψ) ** 2
    grad_field = gradient(field).data
    grad_mag = np.abs(grad_field)

    # Normalize gradient energy relative to intensity
    coherence = float(np.clip(np.mean(np.abs(grad_mag) / (np.mean(intensity) + 1e-9)), 0.0, 1.0))
    phase_avg = float(np.mean(np.angle(ψ)))

    return {
        "intensity_field": intensity,
        "gradient_field": grad_field,
        "gradient_magnitude": grad_mag,
        "ρ": coherence,
        "φ": phase_avg,
        "summary": {
            "mean_intensity": float(np.mean(intensity)),
            "mean_grad": float(np.mean(grad_mag)),
            "coherence": coherence,
            "phase_avg": phase_avg,
        },
    }


# ------------------------------------------------------------
# Self-Test
# ------------------------------------------------------------
if __name__ == "__main__":
    from backend.quant.qtensor.qtensor_field import random_field

    ψ = random_field((4, 4))
    results = collapse_gradient(ψ)

    print("∇ψ summary:")
    for k, v in results["summary"].items():
        print(f"  {k}: {v:.4f}")