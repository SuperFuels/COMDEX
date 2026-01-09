#!/usr/bin/env python3
"""
Fast version of Test B1+B2 - Weak Measurement & Sequential Contextual Normalization
Avoids exponential branching by aggregating ensemble statistics per iteration.
"""

import numpy as np
import matplotlib.pyplot as plt

def normalize(v):
    s = np.sum(v)
    return v if s == 0 else v / s

def born_probs_from_vec(psi):
    a, b = psi
    p0 = float(np.real(np.vdot(a, a)))
    p1 = float(np.real(np.vdot(b, b)))
    s = p0 + p1
    return (p0/s, p1/s)

def renorm_state(psi):
    n = np.linalg.norm(psi)
    return psi if n == 0 else psi / n

# --- quantum weak measurement map ---
def quantum_update_probs(p, mu):
    """Update (p0,p1) after one weak measurement step."""
    p0, p1 = p
    # Kraus map effect on probabilities (approx ensemble-level)
    dp = mu * (p0 * (1 - p0) - p1 * (1 - p1))
    p0p = p0 + dp
    p1p = 1 - p0p
    return normalize([max(p0p, 0), max(p1p, 0)])

# --- photon algebra contextual update ---
def pa_soft_normalize(p, mu):
    p0, p1 = p
    delta = p0 - p1
    p0p = p0 * (1 + mu * delta)
    p1p = p1 * (1 - mu * delta)
    return tuple(normalize([max(p0p, 0), max(p1p, 0)]))

# --- deterministic iteration until convergence ---
def evolve_fast(p_init, updater, tau=1e-3, max_steps=2000):
    p = np.array(p_init, float)
    for k in range(max_steps):
        p_next = np.array(updater(p))
        if np.max(np.abs(p_next - p)) < tau:
            return tuple(p_next), k
        p = p_next
    return tuple(p), max_steps

# --- main ---
if __name__ == "__main__":
    np.random.seed(7)
    r = np.random.randn(2) + 1j * np.random.randn(2)
    psi = renorm_state(r)
    true_p0, true_p1 = born_probs_from_vec(psi)

    mus = [0.05, 0.1, 0.2, 0.4, 0.7, 1.0]
    tau = 1e-6

    print("=== B1+B2 - Weak Measurement & Sequential Contextual Normalization (FAST) ===")
    print(f"Input |ψ⟩ = α|0⟩+β|1⟩ with α={psi[0]:.3f}, β={psi[1]:.3f}")
    print(f"Born target: P(0)={true_p0:.4f}, P(1)={true_p1:.4f}\n")

    rows = []
    for mu in mus:
        pq, kq = evolve_fast((true_p0, true_p1), lambda p: quantum_update_probs(p, mu), tau=tau)
        pa, kp = evolve_fast((true_p0, true_p1), lambda p: pa_soft_normalize(p, mu), tau=tau)
        err_q = abs(pq[0]-true_p0) + abs(pq[1]-true_p1)
        err_p = abs(pa[0]-true_p0) + abs(pa[1]-true_p1)
        rows.append((mu, pq[0], pa[0], kq, kp, err_q, err_p))

    print("μ    |  Quantum P(0)   PA P(0)   steps(QM,PA)   L1err(QM)  L1err(PA)")
    print("-----+---------------------------------------------------------------")
    for mu, pq0, pa0, kq, kp, eq, ep in rows:
        print(f"{mu:0.2f} |    {pq0:0.4f}       {pa0:0.4f}     ({kq:3d},{kp:3d})     {eq:0.2e}    {ep:0.2e}")

    # Plot
    fig, ax = plt.subplots(figsize=(7,4))
    ax.axhline(true_p0, color="k", ls=":", lw=1, label="Born target P(0)")
    ax.plot([r[0] for r in rows], [r[1] for r in rows], "-o", label="Quantum")
    ax.plot([r[0] for r in rows], [r[2] for r in rows], "-o", label="Photon Algebra")
    ax.set_xlabel("Weak-measurement strength μ")
    ax.set_ylabel("Final P(0)")
    ax.set_title("B1+B2 - Weak Measurement Convergence to Born Rule")
    ax.legend()
    plt.tight_layout()
    plt.savefig("PAEV_TestB1B2_WeakMeas_Convergence.png", dpi=160)
    print("\n✅ Saved plot to: PAEV_TestB1B2_WeakMeas_Convergence.png")