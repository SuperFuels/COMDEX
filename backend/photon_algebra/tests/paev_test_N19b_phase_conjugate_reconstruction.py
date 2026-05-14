import json, os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- setup ---
np.random.seed(42)
x = np.linspace(-5, 5, 800)
dx = x[1] - x[0]
psi1_true = (np.exp(-x**2) * (1 + 0.15*np.cos(2.2*x)) * np.exp(1j*0.4*x))

sigma = 0.45
K = np.exp(-(x[:, None] - x[None, :])**2 / (2 * sigma**2))
K /= (np.sqrt(2 * np.pi) * sigma)

phi = 0.12 * np.tanh(x)
psi2 = K @ psi1_true * np.exp(1j * phi)

# --- utility functions ---
def fidelity(a, b):
    na = np.sqrt(np.trapezoid(np.abs(a)**2, x))
    nb = np.sqrt(np.trapezoid(np.abs(b)**2, x))
    return np.abs(np.trapezoid(np.conj(a) * b, x) / (na * nb))

# --- Phase-Conjugate Reconstruction ---
k1d = K[len(x)//2, :] + 1e-12
Psi2 = np.fft.fft(psi2)
Kf = np.fft.fft(k1d)
lam = 1e-3

# Use full complex FFT instead of rFFT
Psi1_rec = (np.conj(Kf) * np.conj(Psi2)) / (np.abs(Kf)**2 + lam)
psi1_rec = np.fft.ifft(Psi1_rec) * np.exp(-1j * phi)

F = fidelity(psi1_true, psi1_rec)

# --- classification ---
if F >= 0.95:
    cls = "✅ Recovered (phase-conjugate match)"
elif F >= 0.80:
    cls = "⚠️ Partial recovery"
else:
    cls = "❌ Not recoverable"

# --- plots ---
os.makedirs("backend/modules/knowledge", exist_ok=True)

plt.figure(figsize=(9, 5))
plt.plot(x, np.real(psi1_true), label="Re[ψ1 true]")
plt.plot(x, np.real(psi1_rec), "--", label="Re[ψ1 rec]")
plt.title("N19b - Phase-Conjugate Reconstruction (real parts)")
plt.xlabel("x")
plt.ylabel("Re[ψ]")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_N19b_Reconstruction_Real.png", dpi=120)

plt.figure(figsize=(9, 5))
plt.plot(x, np.imag(psi1_true), label="Im[ψ1 true]")
plt.plot(x, np.imag(psi1_rec), "--", label="Im[ψ1 rec]")
plt.title("N19b - Phase-Conjugate Reconstruction (imag parts)")
plt.xlabel("x")
plt.ylabel("Im[ψ]")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_N19b_Reconstruction_Imag.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ,
    "G": G,
    "Λ": Λ,
    "α": α,
    "β": β,
    "kernel_sigma": float(sigma),
    "lambda_reg": float(lam),
    "fidelity": float(F),
    "classification": cls,
    "method": "phase-conjugate reconstruction",
    "files": {
        "real_plot": "PAEV_N19b_Reconstruction_Real.png",
        "imag_plot": "PAEV_N19b_Reconstruction_Imag.png",
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}

with open("backend/modules/knowledge/N19b_phase_conjugate_reconstruction.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== N19b - Phase-Conjugate Holographic Reconstruction ===")
print(f"Fidelity={F:.3f} * {cls}")
print("✅ Plots saved and results recorded -> backend/modules/knowledge/N19b_phase_conjugate_reconstruction.json")