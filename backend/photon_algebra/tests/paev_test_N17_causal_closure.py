# backend/photon_algebra/tests/paev_test_N17_causal_closure.py
import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime
from backend.photon_algebra.utils.load_constants import load_constants

const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

print("=== N17 - Causal Loop Closure Test ===")

# Temporal grid
t = np.linspace(0, 10, 2000)
x = np.linspace(-5, 5, 200)

# Initial and evolved states
ψ1 = np.exp(-x**2)[:, None] * np.exp(1j * 0.5 * t)
ψ2 = np.exp(-x**2)[:, None] * np.exp(1j * 0.5 * (t + β * np.sin(t)))

# Feedback closure
ψ1_final = ψ2[:, -1][:, None] * np.exp(1j * β)
fidelity = np.abs(np.vdot(ψ1[:, 0], ψ1_final[:, 0])) / (np.linalg.norm(ψ1[:, 0]) * np.linalg.norm(ψ1_final[:, 0]))
phase_drift = np.angle(np.vdot(ψ1[:, 0], ψ1_final[:, 0]))

# Loop consistency metric
loop_consistency = fidelity * np.cos(phase_drift)

# Classification
if fidelity > 0.99 and abs(phase_drift) < 0.1:
    classification = "✅ Closed"
elif fidelity > 0.7:
    classification = "⚠️ Quasi-closed"
else:
    classification = "❌ Broken"

print(f"ħ={ħ:.3e}, G={G:.1e}, Λ={Λ:.1e}, α={α:.3f}, β={β:.2f}")
print(f"Fidelity={fidelity:.3f}, Phase drift={phase_drift:.3f} rad, Loop metric={loop_consistency:.3f}")
print(f"Classification: {classification}")

# Plot
plt.figure(figsize=(8, 5))
plt.plot(t, np.real(np.exp(1j * β * np.sin(t))), label="Feedback phase modulation")
plt.title("Causal Loop Closure Dynamics")
plt.xlabel("Time (t)")
plt.ylabel("Re[Phase Modulation]")
plt.legend()
plt.grid(True)
plt.savefig("PAEV_N17_CausalClosure.png")

plt.figure(figsize=(8, 5))
plt.plot(x, np.real(ψ1_final[:, 0]), label="Final ψ")
plt.plot(x, np.real(ψ1[:, 0]), '--', label="Initial ψ")
plt.title("Phase Drift Comparison")
plt.legend()
plt.grid(True)
plt.savefig("PAEV_N17_PhaseDrift.png")

summary = {
    "ħ": ħ,
    "G": G,
    "Λ": Λ,
    "α": α,
    "β": β,
    "fidelity": float(fidelity),
    "phase_drift": float(phase_drift),
    "loop_consistency": float(loop_consistency),
    "classification": classification,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/N17_causal_closure.json", "w") as f:
    json.dump(summary, f, indent=2)

print("✅ Plots saved and results recorded -> backend/modules/knowledge/N17_causal_closure.json")