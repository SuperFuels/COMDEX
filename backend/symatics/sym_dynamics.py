"""
───────────────────────────────────────────────
Tessaris Symatics SDK v2.2 (Phase 11)
Module: sym_dynamics.py
───────────────────────────────────────────────
Minimal resonance-collapse time evolution to generate
φ̇(t), μ(t), E_meas(t) traces for the Physics/SDK layer.

Model (simple open-system surrogate):
    dψ/dt = i*ω(t)*ψ  - (μ(t)/2)*ψ
where ω(t) is phase-rotation rate (rad/s), μ(t) is
dimensionless collapse/measurement coupling.

Outputs:
    - psi(t): complex state
    - phi_dot(t): ω(t)
    - mu(t): μ(t)
    - E_meas(t): k_φ * φ̇(t) * μ(t)

Notes:
    - This is a dynamics surrogate to feed SymTactics validators.
    - It does not assert underlying Hamiltonian completeness.
───────────────────────────────────────────────
"""

from __future__ import annotations
import numpy as np

C_LIGHT = 2.99792458e8  # m/s

class SymDynamics:
    @staticmethod
    def evolve(psi0: complex,
               omega: np.ndarray,
               mu: np.ndarray,
               dt: float,
               k_phi: float | None = None):
        """
        Euler integrator for the surrogate Symatics evolution.

        Args
        ----
        psi0 : complex
            Initial complex amplitude/state.
        omega : array-like (rad/s)
            Phase rotation rate trace (φ̇ = ω).
        mu : array-like (dimensionless)
            Collapse/measurement coupling trace.
        dt : float (s)
            Timestep.
        k_phi : float or None
            Phase-collapse constant; defaults to c^2.

        Returns
        -------
        dict with keys: 't','psi','phi_dot','mu','E_meas'
        """
        omega = np.asarray(omega, dtype=float)
        mu = np.asarray(mu, dtype=float)
        assert omega.shape == mu.shape, "omega and mu must match in shape"

        if k_phi is None:
            k_phi = C_LIGHT**2

        n = omega.size
        t = np.arange(n, dtype=float) * dt
        psi = np.empty(n, dtype=np.complex128)
        psi[0] = complex(psi0)

        # dψ/dt = i ω ψ - (μ/2) ψ
        for i in range(1, n):
            dpsi = 1j * omega[i-1] * psi[i-1] - 0.5 * mu[i-1] * psi[i-1]
            psi[i] = psi[i-1] + dt * dpsi

        phi_dot = omega.copy()
        E_meas = k_phi * phi_dot * mu  # bilinear measurement law

        return {
            "t": t,
            "psi": psi,
            "phi_dot": phi_dot,
            "mu": mu,
            "E_meas": E_meas,
            "k_phi": k_phi,
            "dt": dt,
        }

    @staticmethod
    def summarize_energy_balance(trace: dict) -> dict:
        """
        Quick integrals/metrics for regression checks.
        """
        t = trace["t"]; dt = trace["dt"]
        psi = trace["psi"]; E_meas = trace["E_meas"]

        amp = np.abs(psi)
        amp_var = (amp.max() - amp.min()) / (amp.mean() + 1e-12)
        e_int = np.trapezoid(E_meas, dx=dt)

        return {
            "amp_rel_span": float(amp_var),
            "E_integrated": float(e_int),
            "E_mean": float(np.mean(E_meas)),
        }