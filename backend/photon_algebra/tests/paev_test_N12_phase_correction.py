# backend/photon_algebra/tests/paev_test_N12_phase_correction.py
import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime, timezone

ħ = 1e-3
G = 1e-5
Λ0 = 1e-6
α0 = 0.5
β = 0.2

# --- Setup grid ---
x = np.linspace(-5, 5, 200)
t = np.linspace(0, 10, 2000)
X, T = np.meshgrid(x, t, indexing='ij')

# --- Initial encoded message (Gaussian wave) ---
ψ1 = np.exp(-X**2) * np.exp(1j * 0.5 * T)  # shape (200, 2000)

# --- Distortion from bridge overcoupling (same as N11) ---
ψ2_distorted = ψ1 * np.exp(-β * T) * np.exp(1j * 5 * np.sin(T))

# --- Phase correction feedback ---
φ_t = np.exp(-1j * 5 * np.sin(T) * np.exp(-0.5 * T / 10))
ψ2_corrected = ψ2_distorted * φ_t

# --- Fidelity calculation ---
fidelity = np.abs(np.vdot(ψ1, ψ2_corrected)) / (np.linalg.norm(ψ1) * np.linalg.norm(ψ2_corrected))

# --- Plot corrected signal recovery ---
plt.figure(figsize=(10,5))
plt.plot(t, np.real(ψ1[len(x)//2]), label='Input ψ₁', color='blue')
plt.plot(t, np.real(ψ2_corrected[len(x)//2]), label='Recovered ψ₂ (corrected)', linestyle='--', color='orange')
plt.xlabel("t")
plt.ylabel("Signal amplitude")
plt.title("N12 — Phase Correction & Echo Re-stabilization")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("PAEV_N12_PhaseCorrection.png")

# --- Summary output ---
summary = {
    "ħ": ħ,
    "G": G,
    "Λ0": Λ0,
    "α0": α0,
    "β": β,
    "fidelity_corrected": fidelity,
    "classification": "Recovered" if fidelity > 0.9 else "Partially recovered" if fidelity > 0.5 else "Failed",
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
}

print("=== N12 — Phase Correction & Echo Re-stabilization ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ₀={Λ0:.3e}, α₀={α0:.3f}, β={β:.2f}")
print(f"Corrected fidelity = {fidelity:.3f}")
print(f"Classification: {summary['classification']}")
print("✅ Plot saved: PAEV_N12_PhaseCorrection.png")
print("📄 Summary: backend/modules/knowledge/N12_phase_summary.json")

with open("backend/modules/knowledge/N12_phase_summary.json", "w") as f:
    json.dump(summary, f, indent=2)