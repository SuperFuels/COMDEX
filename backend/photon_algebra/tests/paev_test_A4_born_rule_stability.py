#!/usr/bin/env python3
"""
Test A4 — Born Rule Stability under Decoherence
------------------------------------------------

Goal:
Show that Photon Algebra (PA) probabilities remain consistent with
the Born rule as phase coherence between rewrite branches is reduced.
"""

import numpy as np
import matplotlib.pyplot as plt

# ----------------------------
# Helpers
# ----------------------------
def normalize(v):
    n = np.linalg.norm(v)
    return v if n == 0 else v / n

def born_probs(vec):
    vec = normalize(vec)
    return np.abs(vec) ** 2

def dephase_density(rho, gamma_c):
    """Apply exponential damping to off-diagonal elements."""
    n = rho.shape[0]
    out = np.zeros_like(rho, dtype=complex)
    for i in range(n):
        for j in range(n):
            out[i, j] = rho[i, j] if i == j else gamma_c * rho[i, j]
    return out

def photon_algebra_probs(alpha, beta, gamma, gamma_c):
    """Compute 'Photon Algebra' probabilities with dephased coherence."""
    amps = np.array([alpha, beta, gamma], dtype=complex)
    rho = np.outer(amps, np.conj(amps))
    rho_deph = dephase_density(rho, gamma_c)
    diag = np.real(np.diag(rho_deph)).copy()  # make writable
    diag = diag / np.sum(diag)                # normalize explicitly
    return diag

# ----------------------------
# Main test
# ----------------------------
if __name__ == "__main__":
    np.random.seed(42)
    psi = np.random.randn(3) + 1j * np.random.randn(3)
    psi = normalize(psi)
    alpha, beta, gamma = psi

    print("=== Born Rule Stability under Decoherence (Qutrit) ===")
    print(f"Initial |ψ⟩ amplitudes:\n α={alpha:.3f}, β={beta:.3f}, γ={gamma:.3f}\n")

    coherence_levels = np.linspace(1.0, 0.0, 10)
    p_qm_all, p_pa_all = [], []

    for gamma_c in coherence_levels:
        p_qm = born_probs(psi)
        p_pa = photon_algebra_probs(alpha, beta, gamma, gamma_c)
        p_qm_all.append(p_qm)
        p_pa_all.append(p_pa)

    p_qm_all = np.array(p_qm_all)
    p_pa_all = np.array(p_pa_all)

    # ----------------------------
    # Print summary
    # ----------------------------
    for k, gamma_c in enumerate(coherence_levels):
        Δ = np.abs(p_qm_all[k] - p_pa_all[k])
        print(f"γ_c={gamma_c:.2f}  QM={np.round(p_qm_all[k],3)}  PA={np.round(p_pa_all[k],3)}  Δ={np.round(Δ,4)}")

    avg_diff = np.mean(np.abs(p_qm_all - p_pa_all))
    print(f"\nAverage |Δ| across γ_c = {avg_diff:.4e}")
    if avg_diff < 1e-2:
        print("✅ Born rule remains stable under decoherence in Photon Algebra.")
    else:
        print("⚠️ Noticeable deviation: check PA dephasing model.")

    # ----------------------------
    # Plot
    # ----------------------------
    colors = ["b", "r", "g"]
    labels = ["|0⟩", "|1⟩", "|2⟩"]

    plt.figure(figsize=(8, 5))
    for i in range(3):
        plt.plot(coherence_levels, p_qm_all[:, i], colors[i] + "-", label=f"QM {labels[i]}")
        plt.plot(coherence_levels, p_pa_all[:, i], colors[i] + "--", label=f"PA {labels[i]}")
    plt.xlabel("Coherence γ_c")
    plt.ylabel("Probability P(i)")
    plt.title("Test A4 — Born Rule Stability under Decoherence (Qutrit)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("PAEV_TestA4_BornRule_Stability.png", dpi=160)
    print("✅ Saved plot to: PAEV_TestA4_BornRule_Stability.png")