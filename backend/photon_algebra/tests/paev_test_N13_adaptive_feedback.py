import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json

print("=== N13 - Adaptive Feedback Phase Correction & Stability ===")

# Constants
ħ = 1e-3
G = 1e-5
Λ0 = 1e-6
α0 = 0.5
β = 0.2
feedback_gain = 0.3

# Space-time grid
x = np.linspace(-5, 5, 200)
t = np.linspace(0, 10, 2000)
dt = t[1] - t[0]

# Initial conditions
ψ1 = np.exp(-x[:, None]**2) * np.exp(1j * 0.5 * t[None, :])  # initial transmitter signal
ψ2 = np.copy(ψ1) * 0.8  # slightly degraded receiver

# Dynamic parameters
α_t = np.zeros_like(t)
Λ_t = np.zeros_like(t)
fidelity = np.zeros_like(t)

# Adaptive evolution loop
for i in range(1, len(t)):
    # Compute phase difference and feedback correction
    Δφ = np.angle(np.vdot(ψ1[:, i-1], ψ2[:, i-1]))
    phase_correction = np.exp(-1j * feedback_gain * Δφ)

    # Apply phase correction
    ψ2[:, i] = ψ2[:, i-1] * phase_correction

    # Update feedback parameters (self-tuning α and Λ)
    α_t[i] = α0 * (1 + β * np.cos(Δφ))
    Λ_t[i] = Λ0 * (1 - β * np.sin(Δφ))

    # Compute instantaneous fidelity
    fidelity[i] = np.abs(np.vdot(ψ1[:, i], ψ2[:, i]) /
                         (np.linalg.norm(ψ1[:, i]) * np.linalg.norm(ψ2[:, i])))

# Aggregate metrics
mean_fidelity = np.mean(fidelity[int(len(t)*0.8):])  # steady-state fidelity
mean_α_ratio = np.mean(α_t / α0)
mean_Λ_ratio = np.mean(Λ_t / Λ0)

# Classification
if mean_fidelity > 0.9:
    classification = "✅ Self-stabilized (Active Quantum Feedback)"
elif mean_fidelity > 0.7:
    classification = "⚠️ Partial stabilization"
else:
    classification = "❌ Unstable feedback"

# --- Plot 1: Fidelity evolution ---
plt.figure(figsize=(8, 4))
plt.plot(t, fidelity, label="Instantaneous Fidelity |⟨ψ1|ψ2⟩|", color="blue")
plt.axhline(0.9, color="red", linestyle="--", label="90% coherence threshold")
plt.title("N13 - Adaptive Feedback Fidelity")
plt.xlabel("Time")
plt.ylabel("Fidelity")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_N13_FidelityEvolution.png")

# --- Plot 2: α(t) and Λ(t) dynamics ---
plt.figure(figsize=(8, 4))
plt.plot(t, α_t/α0, label="α(t)/α0 - Feedback coupling", color="purple")
plt.plot(t, Λ_t/Λ0, label="Λ(t)/Λ0 - Vacuum drift", color="green")
plt.axhline(1.0, color="gray", linestyle=":")
plt.title("N13 - Dynamic Feedback Response")
plt.xlabel("Time")
plt.ylabel("Relative magnitude")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_N13_FeedbackDynamics.png")

# Output results
summary = {
    "ħ": ħ,
    "G": G,
    "Λ0": Λ0,
    "α0": α0,
    "β": β,
    "feedback_gain": feedback_gain,
    "mean_fidelity": float(mean_fidelity),
    "mean_alpha_ratio": float(mean_α_ratio),
    "mean_lambda_ratio": float(mean_Λ_ratio),
    "classification": classification,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

# Save to backend knowledge base
with open("backend/modules/knowledge/N13_feedback_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"ħ={ħ:.3e}, G={G:.1e}, Λ0={Λ0:.1e}, α0={α0:.3f}, β={β:.2f}, feedback_gain={feedback_gain:.2f}")
print(f"Mean fidelity = {mean_fidelity:.3f}")
print(f"Mean α/α0 = {mean_α_ratio:.3f}, Mean Λ/Λ0 = {mean_Λ_ratio:.3f}")
print(f"Classification: {classification}")
print("✅ Plots saved: PAEV_N13_FidelityEvolution.png, PAEV_N13_FeedbackDynamics.png")
print("📄 Summary: backend/modules/knowledge/N13_feedback_summary.json")
print("----------------------------------------------------------")