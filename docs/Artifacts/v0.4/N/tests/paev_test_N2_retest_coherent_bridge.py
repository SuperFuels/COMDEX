# backend/photon_algebra/tests/paev_test_N2_retest_coherent_bridge.py
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os, json

print("=== N2 (Retest) - Coherent Bridge Activation ===")

# --- Constants ---
ħ, G, Λ0, α0 = 1e-3, 1e-5, 1e-6, 0.5
β = 0.2  # feedback coefficient
t = np.linspace(0, 10, 2000)
x = np.linspace(-5, 5, 200)

# --- Tuned parameters from N3 and N10 ---
α_t = α0 * (1 + 0.1 * np.sin(2 * np.pi * t / 10))     # dynamic coupling (N3)
Λ_t = Λ0 * (0.8 + 0.05 * np.sin(2 * np.pi * t / 5))   # curvature feedback (N10)

# --- Build meshgrid for x,t ---
X, T = np.meshgrid(x, t, indexing="ij")

# --- Source Field ψ1(x,t) ---
ψ1 = np.exp(-X**2) * np.exp(1j * 0.5 * T)  # modulated Gaussian (space+time)

# --- Initialize destination field ψ2(x,t) ---
ψ2 = np.zeros_like(ψ1, dtype=complex)

# --- Time evolution for entangled transfer ---
for i in range(1, len(t)):
    dt = t[i] - t[i - 1]
    ψ2[:, i] = ψ2[:, i - 1] + dt * (
        1j * ħ * α_t[i] * ψ1[:, i] * np.exp(-β * (Λ_t[i] / Λ0 - 1))
    )

# --- Normalization and fidelity check ---
ψ2_norm = ψ2[:, -1] / np.max(np.abs(ψ2))
fidelity = np.abs(np.vdot(ψ1[:, -1], ψ2[:, -1])) / (
    np.linalg.norm(ψ1[:, -1]) * np.linalg.norm(ψ2[:, -1])
)
delay_ratio = 0.6 * (1 - np.real(np.exp(-β * (Λ_t[-1] / Λ0))))

classification = "✅ Active Bridge (Coherent Transfer)" if fidelity > 0.85 else "❌ Inactive Bridge"

print(f"ħ={ħ:.3e}, G={G:.3e}, Λ0={Λ0:.3e}, α0={α0:.3f}, β={β:.2f}")
print(f"Mean α(t)/α0 = {np.mean(α_t/α0):.3f}")
print(f"Mean Λ(t)/Λ0 = {np.mean(Λ_t/Λ0):.3f}")
print(f"Fidelity = {fidelity:.3f}")
print(f"Delay ratio ≈ {delay_ratio:.3f}")
print(f"Classification: {classification}")

# --- Plot the ψ2 response over time ---
ψ2_response = np.abs(np.sum(ψ2, axis=0))
ψ2_response /= np.max(ψ2_response)

plt.figure(figsize=(8, 5))
plt.plot(t, ψ2_response, label="ψ2 response", color="orange")
plt.axvline(4, color="r", linestyle="--", label="Light-cone boundary")
plt.title("N2 (Retest) - Coherent Signal Transfer Across Tuned Bridge")
plt.xlabel("Time")
plt.ylabel("Normalized response amplitude")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_N2_CoherentBridge.png", dpi=200)

# --- Save summary ---
summary = {
    "ħ": ħ,
    "G": G,
    "Λ0": Λ0,
    "α0": α0,
    "β": β,
    "mean_alpha_ratio": float(np.mean(α_t / α0)),
    "mean_lambda_ratio": float(np.mean(Λ_t / Λ0)),
    "fidelity": float(fidelity),
    "delay_ratio": float(delay_ratio),
    "classification": classification,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

os.makedirs("backend/modules/knowledge", exist_ok=True)
with open("backend/modules/knowledge/N2_coherent_retest.json", "w") as f:
    json.dump(summary, f, indent=2)

print("✅ Coherent bridge retest complete. Results saved -> backend/modules/knowledge/N2_coherent_retest.json")