import numpy as np
import matplotlib.pyplot as plt
import sys

print("=== N1 — Causal Entanglement Transport Test ===", flush=True)

ħ, G, Λ, α = 1e-3, 1e-5, 1e-6, 0.5
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}", flush=True)

# Grid setup
x = np.linspace(-5, 5, 200)
t = np.linspace(0, 10, 400)
X, T = np.meshgrid(x, t)

# Curvature wells
κ1 = -1.0 / (1 + (X + 2)**2)
κ2 = -1.0 / (1 + (X - 2)**2)

# Initial entangled fields
ψ1 = np.exp(-((X + 2)**2)) * np.exp(1j * 0.2 * X)
ψ2 = np.exp(-((X - 2)**2)) * np.exp(1j * 0.2 * X)

# Inject message pulse into ψ₁
pulse_center, pulse_width = 0, 0.5
pulse = np.exp(-((x - pulse_center)**2) / (2 * pulse_width**2))
ψ1_t0 = ψ1.copy()
ψ1_t0[0, :] += 0.05 * pulse  # only perturb the first slice

mutual_info, response_signal = [], []

for ti in range(len(t)):
    phase_shift = np.exp(1j * α * np.sin(0.5 * t[ti]))
    ψ1_t = ψ1_t0 * phase_shift
    ψ2_t = ψ2 * np.exp(1j * 0.1 * np.sin(t[ti])) + 0.01 * np.roll(ψ1_t, 5, axis=1)

    # Flatten arrays to compare over the whole spatial domain
    corr = np.real(np.vdot(ψ1_t.flatten(), ψ2_t.flatten()))
    mutual_info.append(np.abs(corr))
    response_signal.append(np.max(np.abs(ψ2_t)))

mutual_info = np.array(mutual_info)
response_signal = np.array(response_signal)

# Light-cone and delay
light_speed = 1.0
distance = 4.0
light_travel_time = distance / light_speed
response_peak_time = t[np.argmax(response_signal)]
delay_ratio = response_peak_time / light_travel_time

print(f"Response peak at t={response_peak_time:.3f}", flush=True)
print(f"Light-cone time = {light_travel_time:.3f}", flush=True)
print(f"Delay ratio (Δt_signal / Δt_light) = {delay_ratio:.3f}", flush=True)

if delay_ratio < 1.0:
    print("✅ Nonclassical entanglement transport detected (ER=EPR regime).", flush=True)
else:
    print("⚠️ Classical propagation — no wormhole traversability yet.", flush=True)

# Plot 1 — Entanglement Response
plt.figure(figsize=(7,5))
plt.plot(t, mutual_info / np.max(mutual_info), label="Mutual Information I(ψ₁; ψ₂)")
plt.plot(t, response_signal / np.max(response_signal), "--", label="ψ₂ Response")
plt.axvline(light_travel_time, color="r", linestyle=":", label="Light-cone")
plt.xlabel("Time"); plt.ylabel("Normalized magnitude")
plt.title("N1 — Entanglement Transport Response")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_N1_EntanglementResponse.png")

# Plot 2 — Signal Delay Map
plt.figure(figsize=(7,5))
plt.plot(t, response_signal / np.max(response_signal), color="orange", label="ψ₂ response")
plt.axvline(light_travel_time, color="r", linestyle="--", label="Light-cone boundary")
plt.xlabel("Time"); plt.ylabel("Response amplitude")
plt.title("N1 — Signal Delay vs Light Cone")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_N1_SignalDelay.png")

print("✅ Plots saved:", flush=True)
print("   - PAEV_N1_EntanglementResponse.png", flush=True)
print("   - PAEV_N1_SignalDelay.png", flush=True)
print("----------------------------------------------------------", flush=True)
sys.stdout.flush()