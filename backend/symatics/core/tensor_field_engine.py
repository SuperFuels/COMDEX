# backend/symatics/core/tensor_field_engine.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.8 - Resonant Tensor Field Engine
# Extends λ-ψ symbolic fluids into λ⊗ψ tensor resonance dynamics.
# Author: Tessaris Core Systems / Codex Intelligence Group
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
import numpy as np
from typing import Tuple, Dict

try:
    from backend.modules.codex.codex_trace import record_event
except ImportError:
    def record_event(event_type: str, **kwargs): return None

def grad_tensor(field: np.ndarray) -> np.ndarray:
    """∇⊗ψ - tensor gradient (outer derivative)"""
    grad_components = np.gradient(field)
    rank2 = np.stack(grad_components, axis=-1)
    return rank2

def divergence_tensor(tensor: np.ndarray) -> np.ndarray:
    """
    ∇*T - Generalized divergence for rank-2+ tensors.
    For tensors with shape (..., N, M), this computes
    divergence along the last axis and sums partials across N dimensions.
    """
    # Handle degenerate or flattened cases
    ndim = tensor.ndim
    if ndim < 3:
        return np.zeros_like(tensor)

    # Compute gradient across all but last axis
    div = np.zeros_like(tensor[..., 0, 0])
    try:
        # Iterate over each spatial dimension
        for i in range(tensor.shape[-2]):
            grad_i = np.gradient(tensor[..., i, :], axis=i, edge_order=1)
            div += np.sum(grad_i, axis=-1)
    except Exception:
        # Fallback to mean gradient if dimensions mismatch
        div = np.mean(np.gradient(np.mean(tensor, axis=(-1, -2))), axis=0)

    record_event("tensor_divergence", mean=float(np.mean(div)), shape=str(tensor.shape))
    return div

class ResonantTensorField:
    """
    Symbolic λ⊗ψ tensor continuum.
    Couples wave ψ and law λ fields via divergence-gradient dynamics.
    """

    def __init__(self, shape=(64, 64), ν=0.2, η=0.05, γ=0.01):
        self.shape = shape
        self.ν = ν      # viscosity / diffusion constant
        self.η = η      # resonant coupling coefficient
        self.γ = γ      # damping factor

        # initialize λ and ψ fields
        self.ψ = np.sin(np.linspace(0, np.pi, shape[0]))[:, None] * np.sin(np.linspace(0, np.pi, shape[1]))[None, :]
        self.λ = np.ones(shape)

        # telemetry history
        self.history = {
            "energy": [],
            "coherence": [],
        }

        record_event("tensor_field_init", shape=str(shape))

    def step(self, dt: float = 0.1):
        """
        Advance λ-ψ tensor field system one time step.
        Uses scalar Laplacian contraction and tensor divergence feedback.
        Numerically stable version with finite guards and smooth λ damping.
        """
        ψ, λ = self.ψ, self.λ

        # Compute Laplacian (scalar contraction of ∇2ψ)
        gradψ = np.gradient(ψ)
        lapψ = sum(np.gradient(g, axis=i) for i, g in enumerate(gradψ))

        # Tensor outer product λ⊗ψ
        λψ_tensor = np.multiply.outer(λ, ψ)

        # Divergence term (rank-consistent)
        div_term = divergence_tensor(λψ_tensor)
        if div_term.shape != ψ.shape:
            collapse_axes = tuple(range(div_term.ndim - 2))
            div_term = np.mean(div_term, axis=collapse_axes) if collapse_axes else div_term

        # ψ evolution (viscous + divergence)
        ψ_next = ψ + dt * (self.ν * lapψ - div_term - self.γ * ψ)
        ψ_next = np.nan_to_num(ψ_next, nan=0.0, posinf=0.0, neginf=0.0)

        # λ evolution (resonant feedback)
        # Use a normalized gradient magnitude as smooth feedback driver
        gradψ_next = np.gradient(ψ_next)
        grad_mag = np.sqrt(sum((g ** 2 for g in gradψ_next)))
        grad_r = float(np.mean(grad_mag))

        # Compute λ update safely
        λ_feedback = self.η * grad_r
        λ_damping = 0.02 * (λ - np.mean(λ))
        λ_next = λ + dt * (λ_feedback - λ_damping)

        # Replace any NaNs/infs with finite values
        λ_next = np.nan_to_num(λ_next, nan=1.0, posinf=2.0, neginf=0.0)

        # Clamp λ for stability
        λ_next = np.clip(λ_next, 0.0, 2.5)

        # Update fields
        self.ψ, self.λ = ψ_next, λ_next

        # Record telemetry
        energy = np.sum(ψ_next ** 2)
        coherence = np.exp(-np.linalg.norm(np.gradient(ψ_next)))
        self.history["energy"].append(energy)
        self.history["coherence"].append(coherence)

        record_event(
            "tensor_field_step",
            mean_lambda=float(np.mean(λ_next)),
            mean_energy=float(energy),
            coherence=float(coherence),
        )

        return ψ_next, λ_next