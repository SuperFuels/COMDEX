import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path

print("=== N2 - Quantum Signal Integrity Test ===")

# Load constants (reuse same TOE constants)
const_path = Path("backend/photon_algebra/constants_v1.1.json")
if const_path.exists():
    constants = json.load(open(const_path))
    ħ = constants["hbar_eff"]
    G = constants["G_eff"]
    Λ = constants["Lambda_eff"]
    α = constants["alpha_eff"]
else:
    ħ, G, Λ, α = 1e-3, 1e-5, 1e-6, 0.5

print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")

# --- Domain setup ---
x = np.linspace(-5, 5, 400)
t = np.linspace(0, 10, 400)
dx = x[1] - x[0]
dt = t[1] - t[0]

# --- Base states (entangled Gaussian pair) ---
ψ1 = np.exp(-x**2) * np.exp(1j * 0.5 * x)
ψ2 = np.exp(-x**2) * np.exp(-1j * 0.5 * x)

# --- Inject modulated message into ψ1 ---
msg = np.exp(-((x - 1)**2) / 0.5**2) * np.sin(10 * x)
ψ1_encoded = ψ1 + 0.2 * msg

# --- Evolution ---
fidelity, decoherence = [], []
for ti in t:
    ψ1_t = ψ1_encoded * np.exp(1j * ħ * ti)
    ψ2_t = ψ2 * np.exp(-1j * ħ * ti)
    overlap = np.vdot(ψ1_t, ψ2_t) / (np.linalg.norm(ψ1_t) * np.linalg.norm(ψ2_t))
    fidelity.append(np.abs(overlap)**2)
    decoherence.append(np.var(np.real(ψ2_t)))

fidelity = np.array(fidelity)
decoherence = np.array(decoherence)

# --- Compute causality margin ---
lightcone_t = 4.0
signal_peak_t = t[np.argmax(fidelity)]
delay_ratio = signal_peak_t / lightcone_t

print(f"Response peak at t={signal_peak_t:.3f}")
print(f"Light-cone time = {lightcone_t:.3f}")
print(f"Delay ratio (Δt_signal / Δt_light) = {delay_ratio:.3f}")

# --- Classification ---
if delay_ratio < 1.0 and np.max(fidelity) > 0.9:
    print("✅ Entanglement-assisted signal transmission verified.")
elif np.max(fidelity) > 0.9:
    print("⚠️ High fidelity but classical timing - possibly non-traversable bridge.")
else:
    print("❌ No coherent transfer detected - bridge inactive.")

# --- Plot results ---
plt.figure(figsize=(8,5))
plt.plot(t, fidelity, label="Fidelity |⟨ψ2|ψ1_encoded⟩|2", color="tab:blue")
plt.plot(t, decoherence / np.max(decoherence), "--", label="Normalized Decoherence", color="tab:orange")
plt.axvline(lightcone_t, color="r", linestyle=":", label="Light-cone")
plt.title("N2 - Quantum Signal Fidelity and Decoherence")
plt.xlabel("Time")
plt.ylabel("Normalized magnitude")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("PAEV_N2_SignalIntegrity.png", dpi=200)

print("✅ Plot saved: PAEV_N2_SignalIntegrity.png")
print("----------------------------------------------------------")