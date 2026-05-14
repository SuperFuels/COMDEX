# backend/symatics/entropy_field.py
# ──────────────────────────────────────────────────────────────
# Tessaris SRK-3 - Field Entropy Kernel (v1.3 Stable)
# Symbolic-Photonic Entropy Feedback Layer + CodexTrace Telemetry
# Author: Tessaris Core Systems / Codex Intelligence Group
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
import numpy as np
from typing import Optional, Any
from dataclasses import dataclass, field

try:
    from backend.modules.codex.codex_trace import record_event
except ImportError:
    def record_event(event_type: str, **fields):
        return None


@dataclass
class EntropyFieldState:
    """
    Represents the S-field (entropy feedback layer) for SRK-3.
    Tracks ψ-density, λ-field amplitude, and computed entropy S.

    Attributes
    ----------
    psi_density : float
        Average |ψ|2 density of the photonic field.
    lambda_t : float
        Current λ-field value or proxy from SRK kernel.
    S : float
        Current Shannon-type field entropy.
    gamma_S : float
        Entropy-dependent damping coefficient γ(S).
    """

    psi_density: float = 0.0
    lambda_t: float = 0.0
    S: float = 0.0
    gamma_S: float = 0.0
    history: list = field(default_factory=list)

    # ──────────────────────────────────────────────
    @staticmethod
    def compute_entropy(psi_values: np.ndarray) -> float:
        """Compute field entropy S = -Σ(p log p) where p = |ψ|2."""
        p = np.clip(np.abs(psi_values) ** 2, 1e-12, 1.0)
        return float(-np.sum(p * np.log(p)))

    @staticmethod
    def entropy_damping(S: float, gamma0: float = 0.05, alpha: float = 0.05) -> float:
        """Entropy-dependent damping γ(S) = γ0 + α*S / (1 + S)."""
        return float(gamma0 + alpha * S / (1.0 + S))

    @staticmethod
    def entropy_gradient(S_prev: float, S_curr: float) -> float:
        """Simple finite-difference gradient estimator ∇S."""
        return float(S_curr - S_prev)

    # ──────────────────────────────────────────────
    def update(self, photonic_field: Any, feedback: Optional[dict] = None):
        """
        Update entropy field state from current photonic field snapshot.
        Expects photonic_field to expose .psi_values or equivalent amplitude array.

        Includes SRK-3 entropy regularization law check (v0.4.6)
        and CodexTrace telemetry emission (v1.3 stable).
        """
        try:
            psi_values = getattr(photonic_field, "psi_values", None)
            if psi_values is None:
                # fallback: synthetic ψ-field to ensure entropy continuity
                psi_values = np.array([
                    complex(1.0, 0.0),
                    complex(0.8, 0.2),
                    complex(0.5, -0.1)
                ])
                record_event("entropy_bootstrap", note="synthetic ψ-field generated")

            # Preserve previous state for Δλ and ΔS estimation
            lambda_prev = getattr(self, "lambda_t", 0.0)
            S_prev = self.S

            # Core entropy computations
            self.psi_density = float(np.mean(np.abs(psi_values) ** 2))
            self.S = self.compute_entropy(psi_values)
            self.gamma_S = self.entropy_damping(self.S)
            gradS = self.entropy_gradient(S_prev, self.S)

            # Example λ feedback (if external SRK field provides updates)
            if hasattr(photonic_field, "lambda_t"):
                self.lambda_t = float(photonic_field.lambda_t)
            else:
                # Default to entropy-based adaptive λ(t)
                self.lambda_t = max(1e-6, 1.0 / (1.0 + self.S))

            # Log base entropy update
            self.history.append({
                "S": self.S,
                "gamma_S": self.gamma_S,
                "gradS": gradS,
            })
            record_event("entropy_update", S=self.S, gamma_S=self.gamma_S, gradS=gradS)

            # ──────────────────────────────────────────────
            # SRK-3 Entropy Regularization Law Check (v0.4.6)
            # ──────────────────────────────────────────────
            from backend.symatics.core.validators.law_check import law_entropy_regularization

            expr = {
                "op": "entropy_feedback",
                "S": self.S,
                "lambda_t": self.lambda_t,
                "lambda_prev": lambda_prev,
            }
            self.last_entropy_feedback = law_entropy_regularization(expr)
            record_event("entropy_law_check", **self.last_entropy_feedback)

            # ──────────────────────────────────────────────
            # CodexTrace emission hook (SRK-3 v1.3)
            # ──────────────────────────────────────────────
            try:
                record_event(
                    "entropy_feedback",
                    S=float(self.S),
                    gamma_S=float(self.gamma_S),
                    gradS=float(gradS),
                    lambda_t=float(self.lambda_t),
                    psi_density=float(self.psi_density),
                    passed=self.last_entropy_feedback.get("passed", True),
                )
            except Exception:
                pass

            # Optionally propagate into feedback dict
            if feedback is not None:
                feedback.update({
                    "entropy_S": self.S,
                    "gamma_S": self.gamma_S,
                    "entropy_feedback": self.last_entropy_feedback,
                })

        except Exception as e:
            record_event("entropy_error", error=str(e))
            raise