import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
import os

# === N8 - Quantum Thermodynamic Limit: Energy Cost of Entanglement Transport ===
ħ = 1e-3
G = 1e-5
Λ = 1e-6
α = 0.5
kB = 1.380649e-23

# Effective surface gravity (analogue)
κ = np.sqrt(Λ / G)

# Effective temperature (Hawking-like)
T = ħ * κ / (2 * np.pi * kB)

# Fidelity sweep
fidelities = np.linspace(1.0, 0.5, 100)
η = α  # Efficiency ~ coupling strength

# Energy cost per bit (Landauer bound analogue)
E_cost = η * kB * T * np.log(2) / fidelities

# Convert to eV for readability
E_cost_eV = E_cost / 1.602176634e-19

# Find threshold where energy cost diverges (low fidelity)
threshold_idx = np.argmin(np.abs(fidelities - 0.9))
E_threshold = E_cost_eV[threshold_idx]

# === Plotting ===
plt.figure(figsize=(8, 6))
plt.plot(fidelities, E_cost_eV, color='blue', label='Energy cost per qubit (eV)')
plt.axhline(E_threshold, color='red', linestyle='--', label=f'90% fidelity cost ≈ {E_threshold:.2e} eV')
plt.xlabel('Fidelity |⟨ψ1|ψ2⟩|2')
plt.ylabel('Energy per bit (eV)')
plt.title('N8 - Quantum Thermodynamic Limit: Energy Cost of Entanglement Transport')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()

out_path = "PAEV_N8_EnergyCost.png"
plt.savefig(out_path)
plt.close()

# === Summary JSON ===
summary = {
    "ħ": ħ,
    "G": G,
    "Λ": Λ,
    "α": α,
    "κ": κ,
    "T": T,
    "E_threshold_eV": E_threshold,
    "fidelity_threshold": 0.9,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

os.makedirs("backend/modules/knowledge", exist_ok=True)
with open("backend/modules/knowledge/N8_energy_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== N8 - Quantum Thermodynamic Limit ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")
print(f"Effective temperature T = {T:.3e} K")
print(f"Energy cost per bit at 90% fidelity = {E_threshold:.3e} eV")
print("✅ Plot saved:", out_path)
print("📄 Summary: backend/modules/knowledge/N8_energy_summary.json")
print("----------------------------------------------------------")