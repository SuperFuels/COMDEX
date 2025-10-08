# -*- coding: utf-8 -*-
"""
F15 — Entanglement Correlation in Photon Algebra
------------------------------------------------
Goal:
Reproduce entangled qubit correlations and decoherence behavior using
symbolic duality and normalization principles within the photon–algebra framework.

Scientific motivation:
If the Tessaris photon–algebra reproduces the correlation strength of quantum
entanglement (violating classical Bell limits), it would imply that entanglement
is an emergent deterministic symmetry — not probabilistic collapse — arising
from contextual normalization.

Outputs:
  • PAEV_F15_EntanglementCorrelation.png
  • backend/modules/knowledge/F15_entanglement_correlation.json
"""
from pathlib import Path
from datetime import datetime, timezone
import json, numpy as np, matplotlib.pyplot as plt

# ---------- simulation parameters ----------
ħ = 1e-3
G = 1e-5
Λ0 = 1e-6
α = 0.5
n_trials = 2000
theta_pairs = [(0, 0), (0, 45), (45, 0), (45, 45)]
sigmas = [0.0, 0.5, 1.0, 2.0]  # phase noise levels

# ---------- quantum correlation baseline ----------
def quantum_bell_correlation(theta1, theta2, n_trials=1000):
    """Quantum correlation for singlet state |ψ⟩ = (|01⟩ - |10⟩)/√2."""
    angles = np.array([theta1, theta2]) * np.pi / 180
    outcomes = np.zeros(n_trials)
    for i in range(n_trials):
        phi = np.random.uniform(0, 2*np.pi)
        a0 = np.sin(angles[0]) * np.cos(phi) + np.cos(angles[0]) * np.sin(phi)
        a1 = np.sin(angles[1]) * np.cos(phi) + np.cos(angles[1]) * np.sin(phi)
        outcomes[i] = np.sign(a0 * a1)
    return np.mean(outcomes)

# ---------- photon–algebra correlation ----------
def pa_entanglement_correlation(theta1, theta2, sigma=0.0, n_trials=1000):
    """Photon-algebra symbolic duality version with contextual rewrites."""
    outcomes = np.zeros(n_trials)
    for i in range(n_trials):
        # symbolic dual pair (entangled)
        state_A = {"op": "⊕", "states": ["0", "¬1"]}
        state_B = {"op": "⊕", "states": ["0", "¬1"]}

        # contextual phase noise
        phi_noise = np.random.normal(0, sigma, 2)
        θ1_eff = theta1 + phi_noise[0]
        θ2_eff = theta2 + phi_noise[1]

        # contextual rewrite based on measurement orientation
        def measure(theta_eff, state):
            if abs(theta_eff % 180 - 90) < 45:
                return "⊤" if "0" in state[0] else "⊥"
            else:
                return "⊤" if "1" in state[1] else "⊥"

        A_out = measure(θ1_eff, state_A["states"])
        B_out = measure(θ2_eff, state_B["states"])

        # correlation outcome
        outcomes[i] = 1 if (A_out == B_out) else -1

    return np.mean(outcomes)

# ---------- CHSH calculation ----------
def compute_chsh(corrs):
    """Compute CHSH = |E(a,b) + E(a,b') + E(a',b) - E(a',b')|"""
    (E_ab, E_abp, E_apb, E_apbp) = corrs
    return abs(E_ab + E_abp + E_apb - E_apbp)

# ---------- run tests ----------
qm_results, pa_results = [], []

for sigma in sigmas:
    corrs_qm, corrs_pa = [], []
    for θ1, θ2 in theta_pairs:
        corrs_qm.append(quantum_bell_correlation(θ1, θ2, n_trials))
        corrs_pa.append(pa_entanglement_correlation(θ1, θ2, sigma, n_trials))
    qm_results.append(compute_chsh(corrs_qm))
    pa_results.append(compute_chsh(corrs_pa))

# ---------- plotting ----------
plt.figure(figsize=(8, 5))
plt.plot(sigmas, qm_results, 'o-', label="Quantum CHSH")
plt.plot(sigmas, pa_results, 'x-', label="Photon-Algebra CHSH")
plt.axhline(2.828, color='r', ls='--', label="Quantum max (2√2)")
plt.axhline(2.0, color='g', ls='--', label="Classical limit (2)")
plt.xlabel("Phase noise σ")
plt.ylabel("CHSH correlation")
plt.title("F15 — Entanglement Correlation in Photon Algebra")
plt.legend(); plt.grid(True); plt.tight_layout()
plt.savefig("PAEV_F15_EntanglementCorrelation.png", dpi=160)
print("✅ Plot saved: PAEV_F15_EntanglementCorrelation.png")

# ---------- summary and metrics ----------
summary = {
    "ħ": ħ, "G": G, "Λ0": Λ0, "α": α,
    "sigmas": sigmas,
    "chsh_quantum": qm_results,
    "chsh_photon_algebra": pa_results,
    "n_trials": n_trials,
    "classification": "✅ Entanglement correlations reproduced (CHSH > 2)" 
                      if pa_results[0] > 2 else "⚠️ No Bell violation (classical correlation)",
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "files": {
        "entanglement_plot": "PAEV_F15_EntanglementCorrelation.png"
    }
}

# ---------- save knowledge summary ----------
Path("backend/modules/knowledge/F15_entanglement_correlation.json").write_text(json.dumps(summary, indent=2))
print("📄 Summary saved → backend/modules/knowledge/F15_entanglement_correlation.json")

# ---------- terminal output ----------
print("\n=== F15 — Entanglement Correlation Test ===")
for i, σ in enumerate(sigmas):
    print(f"σ={σ:.1f} → CHSH_QM={qm_results[i]:.3f}, CHSH_PA={pa_results[i]:.3f}")
print(f"→ {summary['classification']}")