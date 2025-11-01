import json, os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# --- constants loader (uses registry constants_v1.2 etc.) ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- synthetic pair (ψ1 -> channel K -> ψ2), then try to reconstruct ψ1 from ψ2 ---
np.random.seed(42)
x = np.linspace(-5, 5, 800)
dx = x[1] - x[0]

# true input (complex wave)
psi1_true = (np.exp(-x**2) * (1 + 0.15 * np.cos(2.2 * x)) * np.exp(1j * 0.4 * x)).astype(np.complex128)

# holographic/bridge kernel (unknown to recon, but we assume it's approx Gaussian)
sigma = 0.45
K = np.exp(-(x[:, None] - x[None, :])**2 / (2 * sigma**2))
K /= (np.sqrt(2 * np.pi) * sigma)

# forward propagation + mild phase warp
phi = 0.12 * np.tanh(x)
psi2 = (K @ psi1_true) * np.exp(1j * phi)

# --- Reconstruction via Tikhonov deconvolution in Fourier domain ---
# build effective 1D kernel (row sum approx)
k1d = K[len(x) // 2, :].astype(np.complex128)
k1d += 1e-12  # numerical guard

Psi2 = np.fft.fft(psi2)
Kf   = np.fft.fft(k1d)
lam  = 1e-3  # Tikhonov regularization

# Tikhonov inversion
Psi1_rec = (np.conj(Kf) * Psi2) / (np.abs(Kf)**2 + lam)
psi1_rec = np.fft.ifft(Psi1_rec) * np.exp(-1j * phi)  # undo phase warp guess

# --- metrics ---
def fidelity(a, b):
    na = np.sqrt(np.trapz(np.abs(a)**2, x))
    nb = np.sqrt(np.trapz(np.abs(b)**2, x))
    return np.abs(np.trapz(np.conj(a) * b, x) / (na * nb))

F = fidelity(psi1_true, psi1_rec)

# --- plots ---
os.makedirs("backend/modules/knowledge", exist_ok=True)
plt.figure(figsize=(9, 5))
plt.plot(x, np.real(psi1_true), label="Re[ψ1 true]")
plt.plot(x, np.real(psi1_rec), "--", label="Re[ψ1 reconstructed]")
plt.title("N19 - Holographic Reconstruction (real parts)")
plt.xlabel("x"); plt.ylabel("Re[ψ]"); plt.legend(); plt.tight_layout()
plt.savefig("PAEV_N19_Reconstruction_Real.png", dpi=120)

plt.figure(figsize=(9, 5))
plt.plot(x, np.imag(psi1_true), label="Im[ψ1 true]")
plt.plot(x, np.imag(psi1_rec), "--", label="Im[ψ1 reconstructed]")
plt.title("N19 - Holographic Reconstruction (imag parts)")
plt.xlabel("x"); plt.ylabel("Im[ψ]"); plt.legend(); plt.tight_layout()
plt.savefig("PAEV_N19_Reconstruction_Imag.png", dpi=120)

# --- classification ---
if   F >= 0.95: cls = "✅ Resolved (near-perfect)"
elif F >= 0.80: cls = "⚠️ Partial recovery"
else:           cls = "❌ Not recoverable"

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "kernel_sigma": float(sigma),
    "lambda_reg": float(lam),
    "fidelity": float(F),
    "classification": cls,
    "files": {
        "real_plot": "PAEV_N19_Reconstruction_Real.png",
        "imag_plot": "PAEV_N19_Reconstruction_Imag.png",
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
}
with open("backend/modules/knowledge/N19_holographic_reconstruction.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== N19 - Holographic Reconstruction ===")
print(f"Fidelity = {F:.3f} * {cls}")
print("✅ Plots saved and results recorded -> backend/modules/knowledge/N19_holographic_reconstruction.json")