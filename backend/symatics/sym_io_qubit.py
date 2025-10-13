"""
───────────────────────────────────────────────
Tessaris Symatics SDK v2.2
Module: sym_io_qubit.py
───────────────────────────────────────────────
Superconducting qubit interface layer.

Purpose:
    - Map μ ↔ measurement strength (Γₘ)
    - Map φ̇ ↔ Rabi frequency (Ω_R)
    - Enable export/import of experimental traces
───────────────────────────────────────────────
"""

from __future__ import annotations
import numpy as np
from backend.modules.lean.sym_tactics import SymTactics
from backend.modules.lean.sym_tactics_physics import SymPhysics, C_LIGHT


class SymIOQubit:
    @staticmethod
    def generate_trace(omega_r, gamma_m, k_phi=None):
        """
        Parameters
        ----------
        omega_r : array-like
            Rabi frequencies (rad/s)
        gamma_m : array-like
            Measurement strengths (dimensionless)
        """
        omega_r = np.asarray(omega_r, dtype=float)
        gamma_m = np.asarray(gamma_m, dtype=float)
        assert omega_r.shape == gamma_m.shape
        phi_dot = omega_r
        mu = gamma_m
        from backend.modules.lean.sym_tactics_physics import C_LIGHT

        E_meas = (k_phi or C_LIGHT**2) * phi_dot * mu
        return {"phi_dot": phi_dot, "mu": mu, "E_meas": E_meas}

    @staticmethod
    def validate_trace(trace, tol=0.05):
        """Check Symatic law equivalence on qubit data."""
        return SymTactics.energy_mass_equivalence(trace["phi_dot"], trace["mu"], trace["E_meas"], tol=tol)