import numpy as np
from backend.modules.lean.sym_tactics_physics import SymPhysics

def test_infer_mass_from_trace():
    # Optical phase rotation and ultra-weak collapse regime (quantum scale)
    phi_dot = np.linspace(1e14, 3e15, 100)  # rad/s (visible-UV band)
    mu = np.linspace(1e-53, 1e-48, 100)     # ultra-weak collapse probability
    m = SymPhysics.infer_mass_from_trace(phi_dot, mu)
    # Expect mass near subatomic-atomic scale (10^-33-10^-27 kg)
    assert 1e-33 < m < 1e-27

def test_pair_threshold():
    mu = 0.5
    m_e = 9.10938356e-31
    freq = SymPhysics.pair_threshold(mu, m_e)
    assert 1e19 < freq < 1e22  # near gamma-ray frequencies

def test_binding_energy_from_trace():
    phi_dot = np.sin(np.linspace(0, 10*np.pi, 1000)) * 1e12 + 1e12
    mu = np.linspace(0.1, 0.9, 1000)
    E = SymPhysics.binding_energy_from_trace(phi_dot, mu, dt=1e-12)
    assert E > 0
    assert np.isfinite(E)
