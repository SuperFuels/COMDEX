# backend/symatics/core/grad_operators.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.6 — Gradient Operator Layer (∇ Engine)
# Provides differential primitives for Symatics Calculus
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v0.6.1 — October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Dict, Any, Optional
import math
import cmath
import time

try:
    from backend.symatics.core.resonant_laws import ResonantLawEngine
except ImportError:
    ResonantLawEngine = object

# ──────────────────────────────────────────────────────────────
# Telemetry (CodexTrace)
# ──────────────────────────────────────────────────────────────
try:
    from backend.modules.codex.codex_trace import record_event
except ImportError:
    def record_event(event_type: str, **fields):
        """Fallback no-op if telemetry unavailable."""
        return None


# ---------------------------------------------------------------------
# Core Gradient Operators (∇)
# ---------------------------------------------------------------------
def grad_wave(amplitude: float, frequency: float, phase: float) -> float:
    """
    grad_wave (∇wave) — symbolic gradient of wave energy density
    with respect to phase-space. Returns resonance slope magnitude.
    """
    return amplitude * frequency * math.cos(phase)


def grad_energy(E_prev: float, E_next: float, dt: float = 1.0) -> float:
    """grad_energy (∇E) — differential energy drift per timestep."""
    if dt <= 0:
        return 0.0
    return (E_next - E_prev) / dt


def grad_coherence(phi_prev: float, phi_next: float, dt: float = 1.0) -> float:
    """grad_coherence (∇φ) — phase differential representing coherence gradient."""
    if dt <= 0:
        return 0.0
    delta = math.sin(phi_next - phi_prev)
    return delta / dt


# ---------------------------------------------------------------------
# Symbolic Gradient Fusion (Composite Differential)
# ---------------------------------------------------------------------
def compute_gradients(expr_t: Dict[str, Any], expr_t1: Dict[str, Any]) -> Dict[str, float]:
    """
    Computes symbolic gradient components between two symbolic wave states.
    Expected keys: energy, frequency, phase, amplitude.
    """
    A_t = expr_t.get("amplitude", 1.0)
    A_t1 = expr_t1.get("amplitude", 1.0)
    f_t = expr_t.get("frequency", 1.0)
    f_t1 = expr_t1.get("frequency", 1.0)
    phi_t = expr_t.get("phase", 0.0)
    phi_t1 = expr_t1.get("phase", 0.0)
    E_t = expr_t.get("energy", 1.0)
    E_t1 = expr_t1.get("energy", 1.0)

    grad_w = grad_wave((A_t + A_t1) / 2, (f_t + f_t1) / 2, (phi_t + phi_t1) / 2)
    grad_E = grad_energy(E_t, E_t1)
    grad_phi = grad_coherence(phi_t, phi_t1)

    return {"grad_wave": grad_w, "grad_energy": grad_E, "grad_coherence": grad_phi}


# ---------------------------------------------------------------------
# Gradient Integration with ResonantLawEngine
# ---------------------------------------------------------------------
def update_resonant_field(ctx: Any, law_id: str, expr_t: Dict[str, Any], expr_t1: Dict[str, Any]):
    """
    Integrates gradient operators into the ResonantLawEngine.
    Produces a λ-field update based on symbolic differential feedback.
    """
    if not hasattr(ctx, "law_weights") or not isinstance(ctx.law_weights, ResonantLawEngine):
        return None

    grads = compute_gradients(expr_t, expr_t1)
    grad_magnitude = sum(abs(v) for v in grads.values()) / 3.0

    new_lambda = ctx.law_weights.update_with_gradient(
        law_id, deviation=abs(grads["grad_energy"]), grad_r=grad_magnitude
    )

    # Emit telemetry
    try:
        record_event(
            "gradient_field_update",
            law_id=law_id,
            grad_wave=grads["grad_wave"],
            grad_energy=grads["grad_energy"],
            grad_coherence=grads["grad_coherence"],
            lambda_value=new_lambda,
        )
    except Exception:
        pass

    return new_lambda


# ---------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------
if __name__ == "__main__":
    from backend.symatics.core.resonant_laws import ResonantContext
    ctx = ResonantContext()

    state_t = {"amplitude": 1.0, "frequency": 2.0, "phase": 0.1, "energy": 1.0}
    state_t1 = {"amplitude": 1.1, "frequency": 2.2, "phase": 0.3, "energy": 1.05}

    new_lambda = update_resonant_field(ctx, "resonance_continuity", state_t, state_t1)
    print("Updated λ-field:", new_lambda)