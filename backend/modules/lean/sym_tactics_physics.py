"""
───────────────────────────────────────────────
Tessaris Symatics SDK v2.1
Module: sym_tactics_physics.py
───────────────────────────────────────────────
Applied-physics layer for the Symatics Algebra SDK.
Implements measurable counterparts of symbolic relations.

Depends on: backend/modules/sym_tactics.py

Functions:
    infer_mass_from_trace(phi_dot, mu, k_phi)
    pair_threshold(mu, m, k_phi)
    binding_energy_from_trace(phi_dot, mu, k_phi, dt)
    compute_FV_decay(mu, delta_phi)
    simulate_cross_section(mu_values, energy_range, beta)

See /docs/Symatics_Operator_Mapping.md for physical mappings.
───────────────────────────────────────────────
"""

import numpy as np

# Fundamental constants
C_LIGHT = 2.99792458e8      # m/s
H_BAR = 1.054571817e-34     # J·s


class SymPhysics:
    # ---------------------------------------------------------------------
    #  Phase–Collapse Equivalence Laws
    # ---------------------------------------------------------------------
    @staticmethod
    def infer_mass_from_trace(phi_dot, mu, k_phi=None):
        """
        Infer resonant mass equivalent from a phase–collapse trace.

        Args:
            phi_dot (array-like): Phase rotation rate (rad/s).
            mu (array-like): Collapse or measurement rate.
            k_phi (float, optional): Phase–collapse constant. If None, uses c^2.

        Returns:
            float: Inferred effective mass (kg).
        """
        phi_dot = np.asarray(phi_dot)
        mu = np.asarray(mu)
        if k_phi is None:
            k_phi = C_LIGHT**2

        # Average energy rate
        e_meas = k_phi * np.mean(phi_dot * mu)
        # Convert to mass-equivalent (E = m c^2)
        m_eq = e_meas / (C_LIGHT**2)
        return m_eq

    # ---------------------------------------------------------------------
    @staticmethod
    def pair_threshold(mu, m, k_phi=None):
        """
        Compute photon frequency threshold for pair production.

        Args:
            mu (float): Collapse or measurement rate.
            m (float): Particle mass (kg).
            k_phi (float, optional): Phase–collapse constant (default c^2).

        Returns:
            float: Threshold photon frequency (Hz).
        """
        if k_phi is None:
            k_phi = C_LIGHT**2

        # Energy threshold 2mc^2; mapped through Symatic scaling
        e_th = 2 * m * k_phi * mu
        omega_th = e_th / H_BAR
        return omega_th / (2 * np.pi)  # Hz

    # ---------------------------------------------------------------------
    @staticmethod
    def binding_energy_from_trace(phi_dot, mu, k_phi=None, dt=1.0):
        """
        Compute integrated binding energy defect from traces.

        Args:
            phi_dot (array-like): Phase rotation rate (rad/s).
            mu (array-like): Collapse rate or measurement intensity.
            k_phi (float, optional): Phase–collapse constant. If None, uses c^2.
            dt (float): Sampling interval (s).

        Returns:
            float: Integrated binding energy (J).
        """
        phi_dot = np.asarray(phi_dot)
        mu = np.asarray(mu)
        if k_phi is None:
            k_phi = C_LIGHT**2

        e_inst = k_phi * phi_dot * mu
        e_int = np.trapezoid(e_inst, dx=dt)
        return e_int

    # ---------------------------------------------------------------------
    #  Phase 10 — Feynman–Vernon Coherence Layer
    # ---------------------------------------------------------------------
    @staticmethod
    def compute_FV_decay(mu, delta_phi):
        """
        Compute the Feynman–Vernon coherence suppression factor:
            FV = exp[-mu^2 * delta_phi^2]

        Parameters
        ----------
        mu : float or array
            Collapse / measurement coupling coefficient.
        delta_phi : float or array
            Phase variance between alternative histories.

        Returns
        -------
        numpy.ndarray
            Coherence suppression factor (1 -> coherent, 0 -> fully decoherent).
        """
        mu = np.asarray(mu, dtype=float)
        delta_phi = np.asarray(delta_phi, dtype=float)
        return np.exp(-mu**2 * delta_phi**2)

    # ---------------------------------------------------------------------
    @staticmethod
    def simulate_cross_section(mu_values, energy_range, beta=1.0):
        """
        Simulate pair-production cross-section suppression:
            σ(E, μ) = σ_BH(E) * (1 - β * μ^2)

        Parameters
        ----------
        mu_values : list or array
            Measurement couplings to evaluate.
        energy_range : list or array
            Photon energies (MeV or normalized units).
        beta : float
            Coherence-loss coefficient (≈1 near threshold).

        Returns
        -------
        dict
            {mu: σ_ratio(E)} normalized to μ=0 baseline.
        """
        E = np.asarray(energy_range, dtype=float)
        mu_values = np.atleast_1d(mu_values)
        results = {}
        for mu in mu_values:
            ratio = (1.0 - beta * mu**2) * np.ones_like(E)
            results[mu] = ratio
        return results