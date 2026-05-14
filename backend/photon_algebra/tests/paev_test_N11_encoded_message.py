# backend/photon_algebra/tests/paev_test_N11_encoded_message.py
"""
N11 - Encoded Message Transmission & Recovery
Tests full entanglement-mediated communication across the tuned wormhole bridge.
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

ħ, G, Λ0, α0, β = 1e-3, 1e-5, 1e-6, 0.5, 0.2

# Time + spatial domain
t = np.linspace(0, 10, 2000)
x = np.linspace(-1, 1, 200)
ψ0 = np.exp(-x**2 / 0.1)

# Message modulation
ω_m, m = 2.0, 0.1
ψ1 = np.array([
    ψ0 * np.exp(1j * ħ * ti) * (1 + m * np.sin(ω_m * ti))
    for ti in t
])

# Bridge dynamics (simple resonant coupling)
α_t = α0 * (1 + 0.1 * np.sin(β * t))
Λ_t = Λ0 * (1 - 0.2 * np.cos(β * t))

ψ2 = np.zeros_like(ψ1, dtype=complex)
dt = t[1] - t[0]
for i in range(1, len(t)):
    dψ = 1j * ħ * (ψ1[i-1] - ψ2[i-1]) - α_t[i] * (ψ1[i-1] - ψ2[i-1]) - Λ_t[i] * ψ2[i-1]
    ψ2[i] = ψ2[i-1] + dt * dψ

# Extract message signal (real amplitude)
M_in = np.real(ψ1[:, ψ1.shape[1]//2])
M_out = np.real(ψ2[:, ψ2.shape[1]//2])

# Compute fidelity
F = np.dot(M_in, M_out) / (np.linalg.norm(M_in) * np.linalg.norm(M_out))
energy_ratio = np.trapz(np.abs(ψ2[-1])**2, x) / np.trapz(np.abs(ψ1[0])**2, x)

classification = "Recovered" if F > 0.95 else "Degraded"

print("=== N11 - Encoded Message Transmission & Recovery ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ0={Λ0:.3e}, α0={α0:.3f}, β={β:.2f}")
print(f"Fidelity = {F:.3f}")
print(f"Energy ratio (out/in) = {energy_ratio:.3f}")
print(f"Classification: {classification}")

# Plots
plt.figure(figsize=(10,4))
plt.plot(t, M_in, label="Input signal ψ1")
plt.plot(t, M_out, '--', label="Recovered ψ2")
plt.xlabel("t")
plt.ylabel("Signal amplitude")
plt.title("N11 - Encoded Message Transmission & Recovery")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_N11_MessageRecovery.png")

plt.figure(figsize=(6,4))
plt.plot(np.abs(M_in - M_out))
plt.title("Signal Reconstruction Error")
plt.xlabel("t")
plt.ylabel("|ΔM|")
plt.tight_layout()
plt.savefig("PAEV_N11_ErrorProfile.png")

summary = {
    "ħ": ħ,
    "G": G,
    "Λ0": Λ0,
    "α0": α0,
    "β": β,
    "fidelity": float(F),
    "energy_ratio": float(energy_ratio),
    "classification": classification,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

out_path = "backend/modules/knowledge/N11_message_summary.json"
with open(out_path, "w") as f:
    json.dump(summary, f, indent=2)

print(f"✅ Plots saved: PAEV_N11_MessageRecovery.png, PAEV_N11_ErrorProfile.png")
print(f"📄 Summary: {out_path}")
print("----------------------------------------------------------")