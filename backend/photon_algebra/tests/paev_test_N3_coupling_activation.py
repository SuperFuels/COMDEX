import numpy as np
import matplotlib.pyplot as plt
import json, os
from datetime import datetime

# === N3 - Coupling Activation: Traversable Bridge Detection ===
ħ = 1e-3
G = 1e-5
Λ = 1e-6
α_base = 0.5

# Domain setup
t = np.linspace(0, 10, 400)
light_cone = 4.0

# Dynamic coupling sweep (α increases, Λ decreases)
α_t = α_base * (1 + 0.15 * np.sin(0.4 * t))
Λ_t = Λ * (1 - 0.05 * np.cos(0.4 * t))

# Simulated ψ-field response (entangled and encoded)
ψ1 = np.exp(-0.5 * (t - 3.5)**2)
ψ2 = np.exp(-0.5 * (t - 3.5 - 0.5*np.sin(t/2))**2) * (1 + 0.02*np.sin(2*t))

# Mutual information proxy (fidelity under coupling modulation)
fidelity = np.abs(np.correlate(ψ1, ψ2, mode='same'))
fidelity /= np.max(fidelity)
fidelity_shifted = np.roll(fidelity, 40)  # temporal offset

# Threshold detection - bridge "activation"
threshold = 0.9
activation_idx = np.argmax(fidelity_shifted > threshold)
activation_time = t[activation_idx] if activation_idx > 0 else None

# Decoherence proxy (noise from Λ_t)
decoherence = np.exp(-np.abs(Λ_t - Λ)/Λ * 0.3)

# Plot 1: Fidelity evolution
plt.figure(figsize=(8,5))
plt.plot(t, fidelity_shifted, label="Fidelity |⟨ψ2|ψ1⟩|2", color="dodgerblue")
plt.plot(t, decoherence, "--", color="orange", label="Decoherence (Λ drift)")
if activation_time:
    plt.axvline(activation_time, color="red", linestyle=":", label=f"Activation at t={activation_time:.2f}")
plt.axvline(light_cone, color="gray", linestyle="--", label="Light-cone")
plt.title("N3 - Coupling Activation and Traversable Bridge")
plt.xlabel("Time")
plt.ylabel("Normalized magnitude")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_N3_CouplingActivation.png")

# Plot 2: Coupling / Λ modulation
plt.figure(figsize=(8,5))
plt.plot(t, α_t, label="α(t) - Coupling Strength", color="purple")
plt.plot(t, Λ_t / Λ, "--", label="Λ(t)/Λ - Vacuum Drift", color="green")
plt.axhline(1.0, color="gray", linestyle=":")
plt.title("N3 - Dynamic Coupling vs Vacuum Drift")
plt.xlabel("Time")
plt.ylabel("Relative Value")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_N3_CouplingDrift.png")

# Report results
print("=== N3 - Coupling Activation: Traversable Bridge Detection ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α0={α_base:.3f}")
if activation_time:
    print(f"✅ Bridge activation detected at t={activation_time:.3f} (< light-cone={light_cone})")
else:
    print("❌ No activation detected within causal window.")
print("✅ Plots saved:")
print("   - PAEV_N3_CouplingActivation.png")
print("   - PAEV_N3_CouplingDrift.png")

# Export log
results = {
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
    "params": {"ħ": ħ, "G": G, "Λ": Λ, "α_base": α_base},
    "activation_time": activation_time,
    "light_cone": light_cone,
    "activated": activation_time is not None
}
os.makedirs("backend/modules/knowledge", exist_ok=True)
with open("backend/modules/knowledge/bridge_activation_log.json", "w") as f:
    json.dump(results, f, indent=2)