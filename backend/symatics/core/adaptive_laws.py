# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v1.1 - Adaptive Runtime Law Weighting + Δ-Telemetry
# Extends v0.5.1 AdaptiveLawEngine with CodexTrace and internal TelemetryChannel
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v1.1.0 - October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Dict, Optional
import math
import time

# ──────────────────────────────────────────────────────────────
# Telemetry Integration Layer
# ──────────────────────────────────────────────────────────────
# Try CodexTrace first, then fall back to Symatics Δ-Telemetry channel
try:
    from backend.modules.codex.codex_trace import record_event
    TELEMETRY_MODE = "CodexTrace"
except ImportError:
    try:
        from backend.symatics.core.telemetry_channel import record_event
        TELEMETRY_MODE = "SymaticsChannel"
    except ImportError:
        def record_event(event_type: str, **fields):
            """Fallback no-op if no telemetry system is present."""
            return None
        TELEMETRY_MODE = "None"


# ──────────────────────────────────────────────────────────────
# Adaptive Law Engine - λi(t) dynamic coefficient model
# ──────────────────────────────────────────────────────────────
class AdaptiveLawEngine:
    """
    Maintains dynamic law coefficients λi(t) that adapt over time
    in response to runtime measurement drift or resonance imbalance.

    Differential Concept:
        dλi/dt = -η * Δ
    where Δ is the local deviation or symbolic drift metric.

    Each λi(t) corresponds to a symbolic runtime law
    (e.g. "collapse_energy_equivalence") and is continuously adjusted
    during live Symatics evaluation.

    Attributes
    ----------
    weights : Dict[str, float]
        Current λi values for all tracked laws.
    history : Dict[str, list]
        Temporal evolution of λi(t) for audit and telemetry.
    """

    def __init__(self, default_weight: float = 1.0, learning_rate: float = 0.05):
        self.weights: Dict[str, float] = {}
        self.history: Dict[str, list] = {}
        self.learning_rate = learning_rate
        self.default_weight = default_weight
        self.last_update_time = time.time()

    # ──────────────────────────────────────────────────────────────
    def get_weight(self, law_id: str) -> float:
        """Return current λi(t) for given law (defaults to baseline)."""
        return self.weights.get(law_id, self.default_weight)

    # ──────────────────────────────────────────────────────────────
    def update(self, law_id: str, deviation: Optional[float]) -> float:
        """
        Update λi(t) given a measured deviation Δ.

        Parameters
        ----------
        law_id : str
            Identifier of the symbolic law.
        deviation : float or None
            Measured drift (Δ); positive = instability.

        Returns
        -------
        float : Updated λi(t)
        """
        if deviation is None:
            deviation = 0.0

        prev = self.get_weight(law_id)
        Δ = float(deviation)

        # Adaptive gradient update - exponential smoothing
        λ_new = prev * (1.0 - self.learning_rate * Δ)
        λ_new = max(0.0, min(λ_new, 2.0))  # clip for stability

        self.weights[law_id] = λ_new

        now = time.time()
        dt = now - self.last_update_time if self.last_update_time else 1.0
        dλ_dt = (λ_new - prev) / dt
        self.last_update_time = now

        # Store in local history
        self.history.setdefault(law_id, []).append((now, λ_new, Δ))

        # ──────────────────────────────────────────────────────────────
        # Dual Telemetry Emission
        # ──────────────────────────────────────────────────────────────
        try:
            record_event(
                "law_weight_update",
                law_id=law_id,
                prev_weight=prev,
                new_weight=λ_new,
                deviation=Δ,
                lambda_rate=dλ_dt,
                telemetry_mode=TELEMETRY_MODE,
            )
        except Exception:
            # never interrupt runtime adaptation on telemetry errors
            pass

        return λ_new

    # ──────────────────────────────────────────────────────────────
    def summary(self) -> Dict[str, float]:
        """Return all λi(t) in compact form."""
        return dict(self.weights)

    def reset(self):
        """Reset all adaptive weights."""
        self.weights.clear()
        self.history.clear()
        self.last_update_time = time.time()


# ──────────────────────────────────────────────────────────────
# Context Integration Wrapper
# ──────────────────────────────────────────────────────────────
class AdaptiveContext:
    """Lightweight runtime context for integrating AdaptiveLawEngine."""

    def __init__(self):
        self.validate_runtime = True
        self.enable_trace = True
        self.law_weights = AdaptiveLawEngine()


# ──────────────────────────────────────────────────────────────
# Self-test (standalone diagnostic)
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctx = AdaptiveContext()
    print(f"[Telemetry mode: {TELEMETRY_MODE}]")
    for drift in [0.0, 0.05, 0.2, 0.0, -0.1]:
        new_val = ctx.law_weights.update("collapse_energy_equivalence", drift)
        print(f"λ(t) -> {new_val:.3f}")