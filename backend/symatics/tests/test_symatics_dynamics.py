import numpy as np

from backend.symatics.sym_dynamics import SymDynamics
from backend.modules.lean.sym_tactics import SymTactics

def test_dynamics_generates_bilinear_energy_trace():
    # Build simple traces
    n = 2000
    dt = 1e-9  # 1 ns step
    omega = np.linspace(2e6, 8e6, n) * 2*np.pi  # rad/s
    mu = np.linspace(1e-4, 5e-4, n)             # dimensionless

    out = SymDynamics.evolve(psi0=1.0+0j, omega=omega, mu=mu, dt=dt, k_phi=None)

    # Verify E_meas ≈ k_phi * phi_dot * mu via SymTactics (tight tol)
    assert SymTactics.energy_mass_equivalence(out["phi_dot"], out["mu"], out["E_meas"], tol=0.02)

def test_dynamics_energy_summary_is_reasonable():
    n = 1000
    dt = 5e-10
    omega = np.full(n, 5e6 * 2*np.pi)  # constant rotation
    mu = np.linspace(2e-4, 4e-4, n)

    out = SymDynamics.evolve(psi0=1.0+0j, omega=omega, mu=mu, dt=dt)
    summary = SymDynamics.summarize_energy_balance(out)

    # amplitude shouldn't blow up; relative span modest under weak damping
    assert summary["amp_rel_span"] < 0.2
    # integrated energy should be positive and finite
    assert np.isfinite(summary["E_integrated"]) and summary["E_integrated"] > 0.0