# backend/symatics/core/lambda_field.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.7 — λ-Field Tensorization Layer
# Defines λ(ψ, t): continuous adaptive weighting field
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v0.7.0 — October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Dict, Tuple, Any
import numpy as np
import time

try:
    from backend.modules.codex.codex_trace import record_event
except ImportError:
    def record_event(event_type: str, **fields):
        return None


class LambdaField:
    """
    Represents a dynamic λ(ψ, t) field across symbolic wave-space ψ.
    Each law’s adaptive weight becomes a continuous field evolving over time.

    Attributes
    ----------
    field : Dict[str, np.ndarray]
        Continuous λ(ψ, t) values per symbolic law key.
    grid_shape : Tuple[int, int]
        Discretization grid for ψ-space (phase × energy, typically).
    learning_rate : float
        Rate of adaptive diffusion across the field.
    """

    def __init__(self, grid_shape: Tuple[int, int] = (32, 32), learning_rate: float = 0.02):
        self.grid_shape = grid_shape
        self.learning_rate = learning_rate
        self.field: Dict[str, np.ndarray] = {}
        self.timestamp = time.time()

    # ──────────────────────────────────────────────────────────────
    def initialize_law(self, law_id: str, value: float = 1.0):
        """Create a uniform λ-field for a given law."""
        self.field[law_id] = np.full(self.grid_shape, value, dtype=float)

    # ──────────────────────────────────────────────────────────────
    def update(self, law_id: str, deviation_map: np.ndarray):
        """
        Diffuse λ over ψ-space using deviation_map as local perturbation.
        λ(ψ, t+Δt) = λ(ψ, t) * (1 − η·Δψ)
        """
        if law_id not in self.field:
            self.initialize_law(law_id)

        λ = self.field[law_id]
        Δψ = np.clip(deviation_map, -1.0, 1.0)
        λ_new = λ * (1.0 - self.learning_rate * Δψ)
        self.field[law_id] = np.clip(λ_new, 0.0, 2.0)

        record_event("lambda_field_update", law_id=law_id,
                     mean_lambda=float(np.mean(λ_new)),
                     std_lambda=float(np.std(λ_new)))
        self.timestamp = time.time()

    # ──────────────────────────────────────────────────────────────
    def summary(self) -> Dict[str, Dict[str, float]]:
        """Return mean/std stats for each λ-field."""
        return {
            k: {"mean": float(np.mean(v)), "std": float(np.std(v))}
            for k, v in self.field.items()
        }

    # ──────────────────────────────────────────────────────────────
    def reset(self):
        self.field.clear()
        self.timestamp = time.time()