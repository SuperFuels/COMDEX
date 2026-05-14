from backend.symatics.photonic_field import PhotonFieldState, propagate_photon_field, compute_spectral_gradient

def test_photon_field_propagation():
    s = PhotonFieldState(frequency=5.0, amplitude=1+0j, phase=0.0)
    next_s = propagate_photon_field(s)
    assert isinstance(next_s, PhotonFieldState)
    assert 0 <= next_s.intensity() <= 1.0

def test_spectral_gradient_feedback():
    fb = compute_spectral_gradient(ψ_density=0.5, ΔE=0.1)
    assert "spectral_gradient" in fb
    assert "feedback_coeff" in fb
    assert 0 <= fb["spectral_gradient"] <= 1