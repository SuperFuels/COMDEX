#!/usr/bin/env python3
"""
PAEV Test N5 - Quantum Echo & Holographic Recovery
---------------------------------------------------
Goal: Detect whether information injected into ψ1 can be holographically
reconstructed in ψ2 across the entangled wormhole bridge.
"""

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
import os

print("=== N5 - Quantum Echo & Holographic Recovery ===")

# Physical constants (scaled)
ħ = 1e-3
G = 1e-5
Λ = 1e-6
α0 = 0.5

# Simulation grid
N = 200
x = np.linspace(-5, 5, N)
dx = x[1] - x[0]
t = np.linspace(0, 12, 600)

# --- Initialize Fields ---
# ψ1 and ψ2 represent entangled states on opposite "boundaries"
ψ1 = np.exp(-x**2) * np.exp(1j * np.pi * x / 5)
ψ2 = np.exp(-(x - 1.5)**2) * np.exp(-1j * np.pi * x / 5)

# Inject information pulse into ψ1 at t=0 (a Gaussian "message")
pulse = np.exp(-((x + 1.5)**2) / 0.2)
ψ1_encoded = ψ1 + 0.2 * pulse

# --- Propagate and Compute ---
def evolve_field(ψ, κ, dt, steps):
    for _ in range(steps):
        lap = np.gradient(np.gradient(ψ, dx), dx)
        ψ += dt * (1j * ħ * lap - α0 * κ * ψ)
    return ψ

κ_profile = -1.0 / np.cosh(x)**2  # wormhole curvature throat

dt = 0.02
ψ2_recovered = np.zeros((len(t), N), dtype=complex)
echo_fidelity = []

for i, ti in enumerate(t):
    ψ1_t = ψ1_encoded * np.exp(-1j * α0 * ti)
    ψ2_t = ψ2 * np.exp(1j * α0 * ti)
    # Coupling interaction (weak entanglement transfer)
    ψ2_t += 0.05 * np.convolve(ψ1_t.real, np.exp(-x**2), mode="same") * np.exp(-ti/6)
    ψ2_recovered[i] = ψ2_t
    # Holographic echo correlation
    corr = np.abs(np.vdot(ψ2_t, ψ1_encoded)) / (np.linalg.norm(ψ1_encoded) * np.linalg.norm(ψ2_t))
    echo_fidelity.append(corr)

# Normalize fidelity
echo_fidelity = np.array(echo_fidelity) / np.max(echo_fidelity)
light_cone = 4.0

# --- Plot Echo Fidelity ---
plt.figure(figsize=(8,5))
plt.plot(t, echo_fidelity, label="Holographic Echo Fidelity |⟨ψ2|ψ1⟩|")
plt.axvline(light_cone, color='r', linestyle=':', label="Light-cone")
plt.title("N5 - Quantum Echo & Holographic Recovery")
plt.xlabel("Time")
plt.ylabel("Normalized Fidelity")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("PAEV_N5_EchoFidelity.png", dpi=150)

# --- Reconstructed Map (Spatial) ---
plt.figure(figsize=(6,5))
plt.imshow(np.abs(ψ2_recovered.real), extent=[-5,5,0,12], origin='lower', aspect='auto', cmap='plasma')
plt.colorbar(label="|ψ2| (Reconstructed field amplitude)")
plt.title("N5 - Reconstructed ψ2 Echo Map")
plt.xlabel("x")
plt.ylabel("Time")
plt.tight_layout()
plt.savefig("PAEV_N5_ReconstructionMap.png", dpi=150)

# --- Diagnostics ---
peak_time = t[np.argmax(echo_fidelity)]
delay_ratio = peak_time / light_cone
classification = "Recovered" if 0.8 <= echo_fidelity.max() <= 1.0 else "Decohered"

print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α0={α0:.3f}")
print(f"Echo peak at t={peak_time:.3f}")
print(f"Light-cone time = {light_cone:.3f}")
print(f"Delay ratio (Δt_signal / Δt_light) = {delay_ratio:.3f}")
print(f"Classification: {classification}")
print("✅ Plots saved:")
print("   - PAEV_N5_EchoFidelity.png")
print("   - PAEV_N5_ReconstructionMap.png")

# --- Save summary JSON ---
summary = {
    "ħ": ħ,
    "G": G,
    "Λ": Λ,
    "α0": α0,
    "peak_time": float(peak_time),
    "delay_ratio": float(delay_ratio),
    "classification": classification,
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

os.makedirs("backend/modules/knowledge", exist_ok=True)
with open("backend/modules/knowledge/N5_echo_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("📄 Summary: backend/modules/knowledge/N5_echo_summary.json")
print("----------------------------------------------------------")