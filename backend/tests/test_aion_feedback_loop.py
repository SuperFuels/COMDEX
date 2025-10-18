import pytest
from backend.AION.fabric.aion_fabric_feedback import ALPHA, SIGMA_TARGET

def compute_gamma_prime(last_gamma, sigma):
    delta = SIGMA_TARGET - sigma
    return max(0.1, min(2.0, last_gamma + ALPHA * delta))

def test_feedback_increases_gain_when_sigma_low():
    γ_prev = 1.0
    γ_new = compute_gamma_prime(γ_prev, 0.9)
    assert γ_new > γ_prev

def test_feedback_reduces_gain_when_sigma_high():
    γ_prev = 1.0
    γ_new = compute_gamma_prime(γ_prev, 0.99)
    assert γ_new < γ_prev

def test_feedback_clamps_within_limits():
    γ_low = compute_gamma_prime(0.05, 0.0)
    γ_high = compute_gamma_prime(2.5, 1.0)
    assert 0.1 <= γ_low <= 2.0
    assert 0.1 <= γ_high <= 2.0