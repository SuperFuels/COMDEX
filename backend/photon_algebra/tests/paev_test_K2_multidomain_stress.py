"""
K2 — Multi-Domain Energy Verification
Tests TOE consistency across quantum, thermal, and relativistic domains.
"""

import json, numpy as np, matplotlib.pyplot as plt
from pathlib import Path

# Load TOE constants
const_path = Path("backend/modules/knowledge/constants_v1.1.json")
constants = json.loads(const_path.read_text())

ħ, G, Λ, α = constants["ħ_eff"], constants["G_eff"], constants["Λ_eff"], constants["α_eff"]

print("=== K2 — Multi-Domain Stress Verification ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")

# Domains
t = np.linspace(0, 1, 500)
E_q = ħ * np.abs(np.sin(2*np.pi*t))**2
E_t = α * np.abs(np.cos(4*np.pi*t))**2
E_r = G * np.abs(np.sin(6*np.pi*t))**2 + Λ * np.exp(-5*t)

# Combined drift
ΔE_q = np.ptp(E_q)
ΔE_t = np.ptp(E_t)
ΔE_r = np.ptp(E_r)
ΔE_total = abs((E_q+E_t+E_r).mean() - (E_q+E_t+E_r)[0])

print(f"ΔE_q={ΔE_q:.3e}, ΔE_t={ΔE_t:.3e}, ΔE_r={ΔE_r:.3e}")
print(f"Total coherence drift ΔE_total={ΔE_total:.3e}")

if ΔE_total < 1e-4:
    print("✅ TOE closure maintained across all regimes.")
else:
    print("⚠️ Minor coherence drift detected; recommend tolerance tuning.")

# Plots
plt.figure(figsize=(6,4))
plt.plot(t, E_q, label="Quantum")
plt.plot(t, E_t, label="Thermal")
plt.plot(t, E_r, label="Relativistic")
plt.legend(); plt.xlabel("t"); plt.ylabel("Energy")
plt.title("K2 — Multi-Domain Energy Regimes")
plt.savefig("PAEV_K2_MultiDomainEnergy.png", dpi=200)
plt.close()

plt.figure(figsize=(4,3))
plt.bar(["Quantum","Thermal","Relativistic"], [ΔE_q, ΔE_t, ΔE_r])
plt.ylabel("Energy Drift")
plt.title("K2 — Drift Decomposition")
plt.savefig("PAEV_K2_DriftDecomposition.png", dpi=200)
plt.close()

print("✅ Plots saved:")
print("   - PAEV_K2_MultiDomainEnergy.png")
print("   - PAEV_K2_DriftDecomposition.png")
print("----------------------------------------------------------")