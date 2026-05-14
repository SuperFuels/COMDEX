import numpy as np
from backend.modules.lean.sym_tactics_physics import SymPhysics

def test_fv_decay_limits():
    mu = np.linspace(0, 1e-2, 50)
    delta_phi = 1.0
    decay = SymPhysics.compute_FV_decay(mu, delta_phi)
    assert np.isclose(decay[0], 1.0, atol=1e-12)
    assert decay[-1] < 1.0
    assert np.all(decay <= 1.0)

def test_cross_section_ratio():
    mu_values = [0.0, 0.1]
    E = np.linspace(1.0, 5.0, 10)
    res = SymPhysics.simulate_cross_section(mu_values, E)
    assert np.allclose(res[0.0], 1.0)
    assert np.all(res[0.1] < 1.0)