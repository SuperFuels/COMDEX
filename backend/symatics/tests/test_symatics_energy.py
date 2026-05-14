import numpy as np
from backend.modules.lean.sym_tactics import SymTactics

def test_energy_mass_equivalence_pass():
    """Check E ≈ kφ * φ_dot * μ holds for synthetic data."""
    phi_dot = np.linspace(1.0, 10.0, 50)
    mu = np.linspace(0.1, 1.0, 50)
    k_phi_true = 9e16  # roughly c2 in SI units

    E_meas = k_phi_true * phi_dot * mu
    assert SymTactics.energy_mass_equivalence(phi_dot, mu, E_meas, tol=0.05)

def test_energy_mass_equivalence_fail():
    """Deliberately distort bilinear relation using nonlinear phase modulation."""
    import numpy as np
    from backend.modules.lean.sym_tactics import SymTactics

    phi_dot = np.linspace(1.0, 10.0, 200)
    mu = np.linspace(0.1, 1.0, 200)

    # Wild, deceptive pseudo-bilinear energy expression
    E_meas = phi_dot * mu * (1 + 0.3 * np.sin(5 * phi_dot) + 0.2 * np.cos(7 * mu))

    # It *looks* like E ∝ φ̇*μ, but isn't separable - should fail
    assert not SymTactics.energy_mass_equivalence(phi_dot, mu, E_meas, tol=0.05)