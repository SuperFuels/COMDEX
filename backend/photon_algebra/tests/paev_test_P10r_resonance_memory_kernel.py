import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
import json

# ================================================
# P10r - Resonance Memory Kernel Reconstruction
# ================================================

np.random.seed(42)

# --- Load parameters (consistent with P10q) ---
eta = 0.001
noise = 0.0025
K_field = 0.1
K_global = 0.12
T = 1600
M = 3

alignment = dict(
    kappa_align_base=0.06,
    kappa_boost=0.18,
    curvature_gain=0.2,
    phase_damp=0.022,
    merge_bias_gain=0.009,
    bias_gain=0.004
)

# --- Generate phase evolution (same core dynamics) ---
phi = np.zeros((M, T))
phi[0, 0], phi[1, 0], phi[2, 0] = 0.0, 0.4, -0.25
omega = np.array([0.002, -0.001, 0.0005])

def complex_order_parameter(phivec):
    z = np.exp(1j * phivec)
    zbar = z.mean()
    R = np.abs(zbar)
    psi = np.angle(zbar)
    return R, psi

R_hist = np.zeros(T)
for t in range(1, T):
    R, psi = complex_order_parameter(phi[:, t-1])
    R_hist[t] = R
    damp = 0.04 * (1 + 0.6 * (1 - R))
    for i in range(M):
        global_term = K_global * np.sin(psi - phi[i, t-1])
        align_term = -alignment["kappa_align_base"] * np.sin(phi[i, t-1] - np.mean(phi[:, t-1]))
        curvature = -alignment["curvature_gain"] * np.sin(2 * (phi[i, t-1] - np.mean(phi[:, t-1])))
        noise_term = np.random.normal(0, noise)
        phi[i, t] = phi[i, t-1] + eta * (omega[i] + global_term + align_term + curvature - damp * phi[i, t-1] + noise_term)

# Fill last value
R_hist[-1], _ = complex_order_parameter(phi[:, -1])

# --- Compute Memory Kernel K(τ) ---
R_mean = np.mean(R_hist)
R_centered = R_hist - R_mean
autocorr = np.correlate(R_centered, R_centered, mode='full')
autocorr = autocorr[autocorr.size // 2:]  # keep positive lags
K_tau = autocorr / autocorr[0]

tau = np.arange(len(K_tau)) * eta

# --- Fit exponential decay (estimate memory depth) ---
from scipy.optimize import curve_fit

def exp_decay(t, A, tau_m):
    return A * np.exp(-t / tau_m)

try:
    popt, _ = curve_fit(exp_decay, tau[:400], K_tau[:400], p0=[1.0, 0.5])
    A_fit, tau_mem = popt
except Exception:
    A_fit, tau_mem = 1.0, np.nan

# --- Plot ---
plt.figure(figsize=(7,5))
plt.plot(tau, K_tau, label='Measured Kernel', color='royalblue', lw=2)
if not np.isnan(tau_mem):
    plt.plot(tau[:400], exp_decay(tau[:400], *popt), '--', color='darkorange',
             label=f'Exp Fit: τm={tau_mem:.3f}')
plt.title("P10r - Resonance Memory Kernel (Autocorrelation of R(t))")
plt.xlabel("Time lag τ")
plt.ylabel("K(τ)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("PAEV_P10r_ResonanceMemoryKernel.png", dpi=240)
plt.close()

# --- Save JSON summary ---
results = {
    "eta": eta,
    "noise": noise,
    "K_field": K_field,
    "K_global": K_global,
    "alignment": alignment,
    "metrics": {
        "R_mean": float(R_mean),
        "R_final": float(R_hist[-1]),
        "tau_memory": float(tau_mem),
        "A_fit": float(A_fit),
        "K_tau_0": float(K_tau[0]),
        "K_tau_200": float(K_tau[200]),
    },
    "files": {
        "memory_kernel_plot": "PAEV_P10r_ResonanceMemoryKernel.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open("backend/modules/knowledge/P10r_resonance_memory_kernel.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== P10r - Resonance Memory Kernel Reconstruction ===")
print(f"Mean R={results['metrics']['R_mean']:.4f}, Final R={results['metrics']['R_final']:.4f}")
print(f"Estimated Memory τm={results['metrics']['tau_memory']:.3f}")
print("✅ Results saved -> backend/modules/knowledge/P10r_resonance_memory_kernel.json")