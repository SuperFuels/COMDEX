# -*- coding: utf-8 -*-
# File: backend/symatics/photonic_field.py
"""
Tessaris Core v1.1 — SRK-2 Photonic Gradient Kernel
Photonic Field Model ν(x,t) ↔ ψ(t)
─────────────────────────────────────────────
Defines photon field propagation state, spectral gradients, and
energy feedback coupling to the Symatics Reasoning Kernel (SRK-1).

Features
--------
• Photon gradient propagation ν(x,t+Δt)
• Spectral gradient feedback tensor (∇ψ)
• Polarization (σ) and spin (τ) harmonic placeholders
• Designed for integration with SRK λ-field equilibrium loop
"""

from dataclasses import dataclass
from typing import Dict, Any
import math, cmath


# ─────────────────────────────────────────────────────────────
# Core Photon Field Model
# ─────────────────────────────────────────────────────────────
@dataclass
class PhotonFieldState:
    """Represents instantaneous photon gradient state ν(x,t) ↔ ψ(t)."""
    frequency: float           # ν (Hz)
    amplitude: complex         # photon wave amplitude A·e^{iφ}
    phase: float               # φ (radians)
    polarization: float = 0.0  # σ polarization angle
    spin: float = 0.0          # τ spin parameter

    # ─────────────── Derived Quantities ───────────────
    def intensity(self) -> float:
        """Return photon intensity |ψ|²."""
        return float(abs(self.amplitude) ** 2)

    def spectral_density(self) -> float:
        """Spectral density proxy: |A|² × (1 + |ν|)."""
        return float(self.intensity() * (1.0 + abs(self.frequency)))

    # ─────────────── Diagnostics ───────────────
    def coherence_map(self) -> Dict[str, float]:
        """Return diagnostic map for visualization."""
        return {
            "ν": round(self.frequency, 6),
            "|A|": round(abs(self.amplitude), 6),
            "φ": round(self.phase, 6),
            "σ": round(self.polarization, 6),
            "τ": round(self.spin, 6),
            "Sν": round(self.spectral_density(), 6),
        }


# ─────────────────────────────────────────────────────────────
# Photon Propagation Operator
# ─────────────────────────────────────────────────────────────
def propagate_photon_field(state: PhotonFieldState, delta_t: float = 1e-3) -> PhotonFieldState:
    """
    Simple propagation step:
        ν(x,t+Δt) = ν · e^{iφ} · e^{−γ}
    Simulates temporal drift and phase advancement.
    """
    γ = 0.02  # damping coefficient
    φ = state.phase + 2 * math.pi * state.frequency * delta_t
    amp = state.amplitude * cmath.exp(1j * φ) * math.exp(-γ)

    return PhotonFieldState(
        frequency=state.frequency,
        amplitude=amp,
        phase=φ % (2 * math.pi),
        polarization=state.polarization,
        spin=state.spin,
    )


# ─────────────────────────────────────────────────────────────
# Spectral Gradient Tensor
# ─────────────────────────────────────────────────────────────
def compute_spectral_gradient(ψ_density: float, ΔE: float) -> Dict[str, Any]:
    """
    Estimate spectral gradient feedback tensor for SRK coupling.

    Parameters
    ----------
    ψ_density : float
        Normalized ψ-field density
    ΔE : float
        Energy deviation from equilibrium

    Returns
    -------
    dict
        {
            "spectral_gradient": |∇ψ| magnitude,
            "feedback_coeff": stabilizing factor (0–1)
        }
    """
    gradient = abs(math.sin(ψ_density * math.pi)) / (1.0 + abs(ΔE))
    feedback_coeff = round(1.0 - gradient, 6)

    return {
        "spectral_gradient": round(gradient, 6),
        "feedback_coeff": feedback_coeff,
    }