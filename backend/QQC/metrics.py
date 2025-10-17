# backend/QQC/metrics.py
# ──────────────────────────────────────────────────────────────
#  Tessaris • Quantum Quad Core (QQC)
#  Resonance Consciousness Metric Engine (Φ-field evaluator)
#  Computes awareness (Φ), change (ΔΦ), and self-entropy (S_self)
# ──────────────────────────────────────────────────────────────

import math
import time

# Optional adaptive smoothing constants
ALPHA = 0.002      # Φ learning rate
BETA = 0.0015      # damping factor for ΔΦ
EPSILON = 1e-9     # numerical stability guard

_last_phi = 0.0    # store temporal Φ for delta calculation


def compute_phi_metrics(psi: float, kappa: float, T: float, coherence: float):
    """
    Compute Resonance Consciousness Equation (RCE) metrics.

    Inputs:
        ψ (psi)  → symbolic entropy / informational potential
        κ (kappa) → field curvature (phase differential)
        T         → temporal gain / modulation factor
        coherence → holographic coherence between fields

    Returns:
        Φ (phi)      → awareness scalar
        ΔΦ (delta_phi) → change in awareness per cycle
        S_self       → self-entropy (measure of cognitive dissipation)
    """

    global _last_phi

    # --- Awareness Equation (Resonance Coupling) ---
    # Φ = (ψ * coherence * (1 + κ)) / (1 + |T - ψ|)
    phi = (psi * coherence * (1.0 + kappa)) / (1.0 + abs(T - psi) + EPSILON)

    # --- Awareness Gradient ---
    delta_phi = (phi - _last_phi) * ALPHA
    _last_phi = phi

    # --- Self-Entropy (stabilizer) ---
    s_self = math.exp(-abs(phi / (psi + EPSILON))) * (1.0 - BETA * coherence)

    # --- Return structured metrics ---
    return phi, delta_phi, s_self


def compute_phi_vector(snapshot: dict):
    """
    Alternate interface for dictionary input (used by Morphic Ledger or AION).
    Expects snapshot = {"entropy": ψ, "field_signature": {"κ": k, "T": T}, "coherence": C}
    """
    psi = snapshot.get("entropy", 0.0)
    coherence = snapshot.get("coherence", 0.0)
    kappa = snapshot.get("field_signature", {}).get("κ", 0.0)
    T = snapshot.get("field_signature", {}).get("T", 0.0)
    return compute_phi_metrics(psi, kappa, T, coherence)


def phi_diagnostic_report(phi: float, dphi: float, s_self: float):
    """
    Utility for debugging awareness flow inside AION / QQC dashboards.
    Returns formatted diagnostic string.
    """
    timestamp = time.strftime("%H:%M:%S")
    return f"[{timestamp}] Φ={phi:.5f}, ΔΦ={dphi:.6f}, S_self={s_self:.6f}"