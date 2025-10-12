# backend/symatics/core/resonant_laws.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.6 — Resonant Gradient Continuity Engine
# Extends AdaptiveLawEngine with gradient-based λ-field evolution
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v0.6.0 — October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Dict, Optional
import math
import time

try:
    from backend.symatics.core.adaptive_laws import AdaptiveLawEngine
except ImportError:
    AdaptiveLawEngine = object

# ──────────────────────────────────────────────────────────────
# Telemetry (CodexTrace)
# ──────────────────────────────────────────────────────────────
try:
    from backend.modules.codex.codex_trace import record_event
except ImportError:
    def record_event(event_type: str, **fields):
        """Fallback no-op if CodexTrace unavailable."""
        return None


# ---------------------------------------------------------------------
# Resonant Law Engine
# ---------------------------------------------------------------------
class ResonantLawEngine(AdaptiveLawEngine):
    """
    Extends AdaptiveLawEngine with gradient-based λ-field evolution.

    The new update equation integrates resonant feedback ∇R(ψ,t)
    into the λ evolution rule:

        λᵢ(t+Δt) = λᵢ(t) + η(∇Rᵢ - Δᵢ)

    where:
      • grad_r — local resonance gradient (coherence potential)
      • deviation — observed law deviation (instability)
    """

    def update_with_gradient(
        self, law_id: str, deviation: Optional[float], grad_r: Optional[float]
    ) -> float:
        if deviation is None:
            deviation = 0.0
        if grad_r is None:
            grad_r = 0.0

        prev = self.get_weight(law_id)
        delta = float(deviation)
        grad_R = float(grad_r)  # symbolic equivalent of ∇ℛ

        # Resonant gradient update rule
        new_lambda = prev + self.learning_rate * (grad_R - delta)
        new_lambda = max(0.0, min(new_lambda, 2.0))

        self.weights[law_id] = new_lambda

        # Log temporal evolution
        self.history.setdefault(law_id, []).append(
            (time.time(), new_lambda, delta, grad_R)
        )

        # Emit telemetry event
        try:
            record_event(
                "resonant_weight_update",
                law_id=law_id,
                prev_weight=prev,
                new_weight=new_lambda,
                deviation=delta,
                gradient=grad_R,
                learning_rate=self.learning_rate,
            )
        except Exception:
            pass

        return new_lambda

    # -----------------------------------------------------------------
    def gradient_step(self, gradients: Dict[str, float], deviations: Dict[str, float]):
        """
        Apply one full gradient-based update step across all tracked laws.
        """
        for law_id, grad_val in gradients.items():
            dev_val = deviations.get(law_id, 0.0)
            self.update_with_gradient(law_id, dev_val, grad_val)

    # -----------------------------------------------------------------
    def summary(self) -> Dict[str, float]:
        """Return concise λᵢ(t) field summary."""
        return dict(self.weights)


# ---------------------------------------------------------------------
# Integration Context (Testing or Embedding)
# ---------------------------------------------------------------------
class ResonantContext:
    """Lightweight context integrating ResonantLawEngine."""

    def __init__(self):
        self.enable_trace = False
        self.validate_runtime = True
        self.law_weights = ResonantLawEngine()


# ---------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------
if __name__ == "__main__":
    ctx = ResonantContext()
    law = "entanglement_symmetry"
    for step in range(5):
        dev = 0.05 * step
        grad = 0.08 - 0.01 * step
        new_val = ctx.law_weights.update_with_gradient(law, dev, grad)
        print(f"Step {step}: λ={new_val:.4f}")