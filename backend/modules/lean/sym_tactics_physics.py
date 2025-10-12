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

See /docs/Symatics_Operator_Mapping.md for physical mappings.
───────────────────────────────────────────────
"""

import numpy as np

C_LIGHT = 2.99792458e8  # m/s
H_BAR = 1.054571817e-34  # J·s


class SymPhysics:
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

        # average energy rate
        e_meas = k_phi * np.mean(phi_dot * mu)
        # convert to mass-equivalent (E = m c^2)
        m_eq = e_meas / (C_LIGHT**2)
        return m_eq

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

        # Energy threshold 2mc^2; map to Symatic equivalence scaling
        e_th = 2 * m * k_phi * mu
        omega_th = e_th / H_BAR
        return omega_th / (2 * np.pi)  # Hz

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