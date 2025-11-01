# backend/symatics/core/tensor_ops.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.8 - Tensor Calculus Layer
# Symbolic tensor algebra over λ-fields and ψ-space
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v0.8.1 - October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Dict, Tuple
import numpy as np

try:
    from backend.modules.codex.codex_trace import record_event
except ImportError:
    def record_event(event_type: str, **fields):
        return None


# ──────────────────────────────────────────────────────────────
# Fundamental Tensor Operations
# ──────────────────────────────────────────────────────────────
def tensor_outer(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Symbolic tensor product: λ ⊗ ψ"""
    res = np.outer(a.flatten(), b.flatten()).reshape(a.shape + b.shape)
    record_event("tensor_outer", shape=str(res.shape))
    return res


def tensor_contract(tensor: np.ndarray, axes: Tuple[int, int]) -> np.ndarray:
    """Contract a tensor along two axes - inner product ⊗ -> *"""
    res = np.tensordot(tensor, tensor, axes=axes)
    record_event("tensor_contract", axes=str(axes), shape=str(res.shape))
    return res


def tensor_grad(field: np.ndarray) -> np.ndarray:
    """Compute symbolic gradient tensor ∇⊗λ (rank-2 differential tensor)."""
    grads = np.gradient(field)
    grad_tensor = np.stack(grads, axis=-1)
    record_event("tensor_grad", mean=float(np.mean(grad_tensor)))
    return grad_tensor


def tensor_divergence(tensor: np.ndarray) -> np.ndarray:
    """∇*T - Divergence of a rank-2 tensor field."""
    div = np.zeros_like(tensor[..., 0])
    for i in range(tensor.shape[-1]):
        div += np.gradient(tensor[..., i])[i]
    record_event("tensor_divergence", mean=float(np.mean(div)))
    return div


def tensor_measure(field: np.ndarray) -> float:
    """Measurement tensor μ⊗ - quantifies global coherence magnitude."""
    norm = float(np.linalg.norm(field))
    record_event("tensor_measure", norm=norm)
    return norm


# ──────────────────────────────────────────────────────────────
# Composite Tensor Engine
# ──────────────────────────────────────────────────────────────
class TensorEngine:
    """
    Couples λ-fields through symbolic tensor operations to form
    coherent multi-domain Symatic tensors.
    """

    def __init__(self):
        self.registry: Dict[str, np.ndarray] = {}

    def register_field(self, law_id: str, field: np.ndarray):
        """Register a symbolic field λ or ψ for tensor coupling."""
        self.registry[law_id] = field
        record_event("tensor_field_register", law_id=law_id, size=str(field.shape))

    def compute_coupling(self, a_id: str, b_id: str) -> np.ndarray:
        """Compute λ ⊗ ψ coupling tensor."""
        a, b = self.registry[a_id], self.registry[b_id]
        tensor = tensor_outer(a, b)
        record_event("tensor_coupling", a=a_id, b=b_id, mean=float(np.mean(tensor)))
        return tensor

    def coherence_flux(self, law_id: str) -> float:
        """Compute coherence flux Φ⊗ = ||∇⊗λ||"""
        field = self.registry[law_id]
        grad = tensor_grad(field)
        flux = tensor_measure(grad)
        record_event("coherence_flux", law_id=law_id, flux=flux)
        return flux