# backend/symatics/core/calc_ops.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.9 - Symbolic Calculus Precursor Layer
# Defines ∇λ, ∇*λ, and ∇*ψ differential operators
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v0.9.0 - October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Dict
import numpy as np

try:
    from backend.modules.codex.codex_trace import record_event
except ImportError:
    def record_event(event_type: str, **fields):
        return None


# ──────────────────────────────────────────────────────────────
# Fundamental Differential Operators
# ──────────────────────────────────────────────────────────────
def grad_lambda(field: np.ndarray) -> np.ndarray:
    """∇λ - symbolic gradient of λ-field."""
    gx, gy = np.gradient(field)
    grad = np.stack((gx, gy), axis=-1)
    record_event("grad_lambda", mean=float(np.mean(grad)))
    return grad


def div_lambda(field: np.ndarray) -> np.ndarray:
    """∇*λ - divergence of λ-field."""
    gx, gy = np.gradient(field)
    div = gx + gy
    record_event("div_lambda", mean=float(np.mean(div)))
    return div


def curl_psi(field: np.ndarray) -> np.ndarray:
    """∇*ψ - symbolic curl analogue for 2-D ψ-space."""
    fx, fy = np.gradient(field)
    curl = fy - fx
    record_event("curl_psi", mean=float(np.mean(curl)))
    return curl


def continuity_eq(lambda_field: np.ndarray, psi_field: np.ndarray) -> float:
    """
    Symbolic continuity law:
        ∂λ/∂t + ∇*(λψ) ≈ 0
    Returns residual magnitude (deviation from conservation).
    """
    grad_l = grad_lambda(lambda_field)
    div_l = div_lambda(lambda_field)
    flux = np.sum(grad_l * psi_field[..., None], axis=-1)
    residual = np.mean(np.abs(div_l + flux))
    record_event("continuity_eq", residual=float(residual))
    return float(residual)


# ──────────────────────────────────────────────────────────────
# Composite Calculus Engine
# ──────────────────────────────────────────────────────────────
class CalculusEngine:
    """
    High-level interface for symbolic calculus operations.
    """

    def __init__(self):
        self.fields: Dict[str, np.ndarray] = {}

    def register_field(self, name: str, field: np.ndarray):
        self.fields[name] = field

    def differential_profile(self, name: str) -> Dict[str, np.ndarray]:
        field = self.fields[name]
        return {
            "grad": grad_lambda(field),
            "div": div_lambda(field),
            "curl": curl_psi(field),
        }

    def continuity_residual(self, lambda_name: str, psi_name: str) -> float:
        λ = self.fields[lambda_name]
        ψ = self.fields[psi_name]
        return continuity_eq(λ, ψ)