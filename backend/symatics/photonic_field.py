# -*- coding: utf-8 -*-
# File: backend/symatics/photonic_field.py
"""
Tessaris Core v1.2 - SRK Photonic Gradient Kernel
Photonic Field Model ν(x,t) ↔ ψ(t)
─────────────────────────────────────────────
Extends v1.1 with:
  * Synthetic ψ-field generator for SRK-3/4 coupling
  * Cached ψ-density tracking
  * Safe coherence diagnostics for entropy/resonance feedback

Defines photon field propagation state, spectral gradients, and
energy feedback coupling to the Symatics Reasoning Kernel (SRK-1).

Features
--------
* Photon gradient propagation ν(x,t+Δt)
* Spectral gradient feedback tensor (∇ψ)
* Polarization (σ) and spin (τ) harmonic placeholders
* ψ-field sampling for SRK-3 entropy + SRK-4 resonance
* Designed for integration with SRK λ-field equilibrium loop
"""

from dataclasses import dataclass, field
from typing import Dict, Any
import math, cmath, numpy as np


# ─────────────────────────────────────────────────────────────
# Core Photon Field Model
# ─────────────────────────────────────────────────────────────
@dataclass
class PhotonFieldState:
    """Represents instantaneous photon gradient state ν(x,t) ↔ ψ(t)."""
    frequency: float           # ν (Hz)
    amplitude: complex         # photon wave amplitude A*e^{iφ}
    phase: float               # φ (radians)
    polarization: float = 0.0  # σ polarization angle
    spin: float = 0.0          # τ spin parameter
    psi_density: float = field(default=1.0, init=False)  # cached ψ2 mean

    # ─────────────── Derived Quantities ───────────────
    def intensity(self) -> float:
        """Return photon intensity |ψ|2."""
        return float(abs(self.amplitude) ** 2)

    def spectral_density(self) -> float:
        """Spectral density proxy: |A|2 * (1 + |ν|)."""
        return float(self.intensity() * (1.0 + abs(self.frequency)))

    @property
    def psi_values(self):
        """
        Synthetic ψ-field samples derived from amplitude and phase.
        Provides SRK-3/4 with ψ(t) lattice for entropy/resonance analysis.
        """
        try:
            amp = abs(self.amplitude) if hasattr(self, "amplitude") else 1.0
            phase = getattr(self, "phase", 0.0)
            t = np.linspace(0, 2 * np.pi, 32)
            psi = amp * np.exp(1j * (t + phase))
            # Cache ψ-density (mean |ψ|2)
            self.psi_density = float(np.mean(np.abs(psi) ** 2))
            return psi
        except Exception:
            self.psi_density = 1.0
            return np.array([complex(1.0, 0.0)])

    # ─────────────── Diagnostics ───────────────
    def coherence_map(self) -> Dict[str, float]:
        """Return diagnostic map for visualization."""
        return {
            "ν": round(self.frequency, 6),
            "|A|": round(abs(self.amplitude), 6),
            "φ": round(self.phase, 6),
            "σ": round(self.polarization, 6),
            "τ": round(self.spin, 6),
            "ψ2": round(self.psi_density, 6),
            "Sν": round(self.spectral_density(), 6),
        }


# ─────────────────────────────────────────────────────────────
# Photon Propagation Operator
# ─────────────────────────────────────────────────────────────
def propagate_photon_field(state: PhotonFieldState, delta_t: float = 1e-3) -> PhotonFieldState:
    """
    Simple propagation step:
        ν(x,t+Δt) = ν * e^{iφ} * e^{-γ}
    Simulates temporal drift and phase advancement.
    """
    γ = 0.02  # damping coefficient
    φ = state.phase + 2 * math.pi * state.frequency * delta_t
    amp = state.amplitude * cmath.exp(1j * φ) * math.exp(-γ)

    new_state = PhotonFieldState(
        frequency=state.frequency,
        amplitude=amp,
        phase=φ % (2 * math.pi),
        polarization=state.polarization,
        spin=state.spin,
    )
    # Maintain ψ-density continuity
    _ = new_state.psi_values
    return new_state


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
            "feedback_coeff": stabilizing factor (0-1)
        }
    """
    gradient = abs(math.sin(ψ_density * math.pi)) / (1.0 + abs(ΔE))
    feedback_coeff = round(1.0 - gradient, 6)

    return {
        "spectral_gradient": round(gradient, 6),
        "feedback_coeff": feedback_coeff,
    }