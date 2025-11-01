# backend/symatics/core/resonant_laws.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.6.2 - Resonant Gradient Continuity Engine
# Provides adaptive resonance law updates with gradient feedback
# and analytic coherence metric R(ψ,t) = E + αC.
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v0.6.2 - October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Dict, Optional
import math
import time

try:
    from backend.modules.codex.codex_trace import record_event
except ImportError:
    def record_event(event_type: str, **fields):
        """Fallback no-op if CodexTrace unavailable."""
        return None


# ──────────────────────────────────────────────────────────────
# Resonance metric helper: R(ψ,t) = E + αC
# ──────────────────────────────────────────────────────────────
def compute_resonance_metric(energy: float, coherence: float, alpha: float = 0.25) -> float:
    """
    Analytic resonance metric R(ψ,t) = E + αC.
    Provides smoother λ feedback via coherence weighting.
    """
    if energy is None:
        energy = 0.0
    if coherence is None:
        coherence = 0.0
    return float(energy) + alpha * float(coherence)


# ──────────────────────────────────────────────────────────────
# Resonant Law Engine
# ──────────────────────────────────────────────────────────────
class ResonantLawEngine:
    """
    Maintains λi(t) coefficients for resonance-driven symbolic laws.
    Extends AdaptiveLawEngine with gradient-aware correction and R(ψ,t) weighting.
    """

    def __init__(self, default_weight: float = 1.0, learning_rate: float = 0.05):
        self.weights: Dict[str, float] = {}
        self.history: Dict[str, list] = {}
        self.learning_rate = learning_rate
        self.default_weight = default_weight

    # ──────────────────────────────────────────────────────────────
    def get_weight(self, law_id: str) -> float:
        """Return λi(t) for given law, default to baseline."""
        return self.weights.get(law_id, self.default_weight)

    # ──────────────────────────────────────────────────────────────
    def update_with_gradient(
        self,
        law_id: str,
        deviation: float,
        grad_r: Optional[float] = None,
        energy: Optional[float] = None,
        coherence: Optional[float] = None,
    ) -> float:
        """
        Update λi(t) given deviation Δ, gradient magnitude ∇R, and optional energy/coherence.
        Implements feedback law:
            dλ/dt = η * (∇R - Δ)
        where R(ψ,t) = E + αC smooths the correction.
        """
        if deviation is None:
            deviation = 0.0
        if grad_r is None:
            grad_r = 0.0

        prev = self.get_weight(law_id)
        R_val = compute_resonance_metric(energy, coherence)

        # Composite correction term
        grad_term = float(grad_r)
        delta_term = float(deviation)
        correction = self.learning_rate * ((0.5 * grad_term * R_val) - delta_term)

        new_lambda = prev + correction
        new_lambda = max(0.0, min(new_lambda, 2.0))

        self.weights[law_id] = new_lambda
        self.history.setdefault(law_id, []).append(
            (time.time(), new_lambda, deviation, grad_term, R_val)
        )

        # Telemetry event
        try:
            record_event(
                "resonant_law_update",
                law_id=law_id,
                prev_weight=prev,
                new_weight=new_lambda,
                deviation=delta_term,
                grad_magnitude=grad_term,
                resonance_metric=R_val,
            )
        except Exception:
            pass

        return new_lambda

    # ──────────────────────────────────────────────────────────────
    def summary(self) -> Dict[str, float]:
        """Return all λi(t) in compact form."""
        return dict(self.weights)

    # ──────────────────────────────────────────────────────────────
    def reset(self):
        """Reset resonance state."""
        self.weights.clear()
        self.history.clear()

# backend/symatics/core/resonant_laws.py
def update_with_gradient(self, law_id: str, deviation: float, grad_r: Optional[float] = None) -> float:
    """
    Update λi(t) given deviation Δ and gradient magnitude grad_r.
    Incorporates analytic coherence weighting for smoother resonance damping.
    """
    if deviation is None:
        deviation = 0.0
    if grad_r is None:
        grad_r = 0.0

    prev = self.get_weight(law_id)
    delta_term = float(deviation)
    grad_term = float(grad_r)

    # --- NEW: analytic coherence weighting term ---
    coherence_metric = math.exp(-abs(grad_term))        # smoother λ feedback
    correction = self.learning_rate * ((grad_term * coherence_metric) - delta_term)
    new_lambda = prev + correction

    new_lambda = max(0.0, min(new_lambda, 2.0))
    self.weights[law_id] = new_lambda
    self.history.setdefault(law_id, []).append(
        (time.time(), new_lambda, deviation, grad_term)
    )

    try:
        record_event(
            "resonant_law_update",
            law_id=law_id,
            deviation=delta_term,
            grad_magnitude=grad_term,
            coherence_metric=coherence_metric,
            lambda_value=new_lambda,
        )
    except Exception:
        pass

    return new_lambda
# ──────────────────────────────────────────────────────────────
# Resonant Context Wrapper
# ──────────────────────────────────────────────────────────────
class ResonantContext:
    """Context wrapper providing a ResonantLawEngine."""
    def __init__(self):
        self.enable_trace = True
        self.law_weights = ResonantLawEngine()