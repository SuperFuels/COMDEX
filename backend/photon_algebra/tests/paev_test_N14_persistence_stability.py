import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# === N14 - Quantum Information Persistence & Closed-Loop Stability ===

ħ = 1e-3
G = 1e-5
Λ0 = 1e-6
α0 = 0.5
β = 0.2
feedback_gain = 0.3
cycles = 3

# Time and signal setup
t = np.linspace(0, 10, 2000)
ψ1 = np.exp(1j * 0.5 * t) * np.exp(-0.05 * t)  # base coherent signal
fidelities, energy_ratios, phase_errors = [], [], []

ψ_prev = ψ1.copy()

for i in range(cycles):
    # Simulate noise, curvature drift, and feedback correction
    σ = 0.01 * (i + 1)
    noise = σ * (np.random.randn(len(t)) + 1j * np.random.randn(len(t)))
    Λt = Λ0 * (1 + 0.05 * np.sin(0.5 * t))
    αt = α0 * (1 + feedback_gain * np.cos(0.5 * t))

    ψ_next = ψ_prev * np.exp(-1j * β * t) + noise
    ψ_next *= np.exp(-0.5 * σ * t) * (αt.mean() / α0)

    # Fidelity and metrics
    fidelity = np.abs(np.vdot(ψ1, ψ_next) / (np.linalg.norm(ψ1) * np.linalg.norm(ψ_next))) ** 2
    energy_ratio = np.trapz(np.abs(ψ_next)**2, t) / np.trapz(np.abs(ψ1)**2, t)
    phase_error = np.angle(np.vdot(ψ1, ψ_next))
    
    fidelities.append(fidelity)
    energy_ratios.append(energy_ratio)
    phase_errors.append(phase_error)

    ψ_prev = ψ_next.copy()

mean_fid = np.mean(fidelities)
classification = (
    "✅ Persistent Information Loop"
    if mean_fid > 0.9 else
    "⚠️ Partial Retention" if mean_fid > 0.5 else
    "❌ Lossy Loop"
)

# === Visualization ===
plt.figure(figsize=(8,4))
plt.plot(range(1, cycles+1), fidelities, 'o-', label='Fidelity per cycle')
plt.axhline(0.9, color='r', ls='--', label='90% threshold')
plt.xlabel('Cycle')
plt.ylabel('Fidelity |⟨ψ1|ψi⟩|2')
plt.title('N14 - Information Persistence per Feedback Cycle')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("PAEV_N14_PersistenceCycles.png")

plt.figure(figsize=(8,4))
plt.plot(range(1, cycles+1), np.unwrap(phase_errors), 'o-', color='orange')
plt.title("N14 - Phase Drift Across Feedback Cycles")
plt.xlabel("Cycle")
plt.ylabel("Phase error (radians)")
plt.grid(True)
plt.tight_layout()
plt.savefig("PAEV_N14_PhaseDrift.png")

summary = {
    "ħ": ħ,
    "G": G,
    "Λ0": Λ0,
    "α0": α0,
    "β": β,
    "feedback_gain": feedback_gain,
    "cycles": cycles,
    "fidelities": fidelities,
    "mean_fidelity": mean_fid,
    "energy_ratios": energy_ratios,
    "phase_errors": phase_errors,
    "classification": classification,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/N14_persistence_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== N14 - Quantum Information Persistence & Closed-Loop Stability ===")
print(f"ħ={ħ:.3e}, G={G:.1e}, Λ0={Λ0:.1e}, α0={α0:.3f}, β={β:.2f}")
print(f"Feedback gain={feedback_gain:.2f}, cycles={cycles}")
print(f"Mean fidelity={mean_fid:.3f}")
print(f"Classification: {classification}")
print("✅ Plots saved: PAEV_N14_PersistenceCycles.png, PAEV_N14_PhaseDrift.png")
print("📄 Summary: backend/modules/knowledge/N14_persistence_summary.json")
print("----------------------------------------------------------")