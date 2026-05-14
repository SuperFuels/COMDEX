import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# ============================================
# P10s - Kernel Spectral Decomposition
# ============================================

# --- Load K(τ) from P10r (or recompute from R(t) if needed) ---
jpath = Path("backend/modules/knowledge/P10r_resonance_memory_kernel.json")
with open(jpath, "r") as f:
    j = json.load(f)

eta = j["eta"]
# We'll reconstruct K(τ) from the saved plot data source if present; otherwise,
# re-estimate from the model by regenerating a short R(t) run matching P10r.

# For simplicity, re-generate R_hist using the same params and compute K(τ)
np.random.seed(42)
T = 1600
M = 3
phi = np.zeros((M, T))
phi[0, 0], phi[1, 0], phi[2, 0] = 0.0, 0.4, -0.25

noise = j["noise"]; K_field = j["K_field"]; K_global = j["K_global"]
align = j["alignment"]
omega = np.array([0.002, -0.001, 0.0005])

def complex_order_parameter(phivec):
    z = np.exp(1j*phivec)
    zb = z.mean()
    R = np.abs(zb); psi = np.angle(zb)
    return R, psi

R_hist = np.zeros(T)
for t in range(1, T):
    R, psi = complex_order_parameter(phi[:, t-1])
    R_hist[t] = R
    damp = 0.04 * (1 + 0.6 * (1 - R))
    for i in range(M):
        global_term = K_global * np.sin(psi - phi[i, t-1])
        align_term = -align["kappa_align_base"] * np.sin(phi[i, t-1] - np.mean(phi[:, t-1]))
        curvature  = -align["curvature_gain"] * np.sin(2*(phi[i, t-1]-np.mean(phi[:, t-1])))
        xi = np.random.normal(0, noise)
        phi[i, t] = phi[i, t-1] + eta*(omega[i] + global_term + align_term + curvature
                                       - damp*phi[i, t-1] + xi)

# autocorr (memory kernel)
R_c = R_hist - R_hist.mean()
ac = np.correlate(R_c, R_c, mode="full")
ac = ac[ac.size//2:]
K_tau = ac / ac[0]
N = len(K_tau)
dt = eta
# --- Spectrum of K(τ): use real FFT of kernel ---
# zero-pad for finer frequency grid
pad = 4
K_pad = np.pad(K_tau, (0, (pad-1)*N), mode='constant')
S = np.fft.rfft(K_pad) * dt
freq = np.fft.rfftfreq(K_pad.size, d=dt)
PSD = np.abs(S)**2

# normalize for comparability
PSD /= PSD.max()

# --- Extract peak, -3 dB bandwidth, Q ---
peak_idx = int(np.argmax(PSD))
f_peak = float(freq[peak_idx])
half_pow = 10**(-3/10)  # -3 dB
# find nearest indices left/right where PSD drops to half_pow
def nearest_crossing(x, y, ylevel, start, step):
    i = start
    while 0 <= i < len(y):
        if y[i] <= ylevel:
            return i
        i += step
    return None

left = nearest_crossing(freq, PSD, half_pow, peak_idx, -1)
right = nearest_crossing(freq, PSD, half_pow, peak_idx, +1)

if left is not None and right is not None and right > left:
    bw_3db = float(freq[right] - freq[left])
    Q = float(f_peak / bw_3db) if bw_3db > 0 else float("inf")
else:
    bw_3db = float("nan"); Q = float("nan")

# --- Plots ---
plt.figure(figsize=(9,4.8))
plt.plot(freq, PSD, lw=2, label="|FFT{K(τ)}|2 (norm)")
plt.axvline(f_peak, color='crimson', ls='--', label=f"f_peak={f_peak:.3f}")
if np.isfinite(bw_3db):
    plt.hlines(half_pow, freq[left], freq[right], colors='orange', linestyles='--',
               label=f"-3 dB BW={bw_3db:.3f}")
plt.yscale("log")
plt.xlabel("frequency (a.u.)"); plt.ylabel("normalized power (log)")
plt.title("P10s - Kernel Spectrum (Resonance & Bandwidth)")
plt.grid(alpha=0.25, which='both')
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P10s_KernelSpectrum.png", dpi=240)
plt.close()

# linear-scale inset (optional quick second plot)
plt.figure(figsize=(9,4.2))
plt.plot(freq, PSD, lw=2)
plt.xlabel("frequency (a.u.)"); plt.ylabel("normalized power")
plt.title("P10s - Kernel Spectrum (linear)")
plt.grid(alpha=0.25)
plt.tight_layout()
plt.savefig("PAEV_P10s_KernelSpectrum_linear.png", dpi=240)
plt.close()

# --- Save JSON ---
out = {
    "eta": eta,
    "dt": dt,
    "N_kernel": int(N),
    "padding": pad,
    "f_peak": f_peak,
    "bw_3db": bw_3db,
    "Q": Q,
    "metrics": {
        "PSD_max": 1.0,
        "half_power_level": half_pow
    },
    "files": {
        "spectrum_log": "PAEV_P10s_KernelSpectrum.png",
        "spectrum_linear": "PAEV_P10s_KernelSpectrum_linear.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
Path("backend/modules/knowledge").mkdir(parents=True, exist_ok=True)
with open("backend/modules/knowledge/P10s_kernel_spectrum.json", "w") as f:
    json.dump(out, f, indent=2)

print("=== P10s - Kernel Spectral Decomposition ===")
print(f"f_peak={f_peak:.4f}, BW_3dB={bw_3db:.4f}, Q={Q:.2f}")
print("✅ Results saved -> backend/modules/knowledge/P10s_kernel_spectrum.json")