#!/usr/bin/env python3
import numpy as np, json, matplotlib.pyplot as plt, time
from pathlib import Path

# --- stable repo-relative paths ---
# Resolve repo root robustly
here = Path(__file__).resolve()
# tests -> photon_algebra -> backend -> <repo-root>
REPO = here.parents[3]  # correct root (.../COMDEX)
TESTS_DIR = REPO / "backend/photon_algebra/tests"
CONST_DIR = REPO / "backend/photon_algebra/constants"
TESTS_DIR.mkdir(parents=True, exist_ok=True)
CONST_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILE  = TESTS_DIR / "results_G9_emergent_gravity_coupling.csv"
PLOT_FILE = TESTS_DIR / "PAEV_TestG9_EmergentCoupling.png"
JSON_FILE = CONST_DIR / "G9_emergent_gravity_coupling.json"

print("=== Test G9 - Emergent Gravity-Quantum Coupling ===")

# --- simulation parameters ---
steps = 1000
t = np.linspace(0, 10, steps)
np.random.seed(42)

psi = np.sin(2*np.pi*0.5*t) + 0.05*np.random.randn(steps)
kappa = 0.8*np.sin(2*np.pi*0.5*t + 0.2) + 0.05*np.random.randn(steps)
energy = psi**2 + kappa**2
psi_kappa = psi * kappa

spectral_entropy = np.zeros(steps)
for i in range(steps):
    seg = psi[max(0, i-200):i+1]
    if len(seg) > 32:
        p = np.abs(np.fft.rfft(seg))**2
        p /= np.sum(p) + 1e-12
        spectral_entropy[i] = -np.sum(p*np.log2(p+1e-12))
    else:
        spectral_entropy[i] = np.nan

# --- results ---
final_E  = float(np.mean(energy[-100:]))
final_PK = float(np.mean(psi_kappa[-100:]))
final_SE = float(np.nanmean(spectral_entropy[-100:]))

print(f"⟨E⟩ final = {final_E:.6e}")
print(f"⟨ψ*κ⟩ final = {final_PK:.6e}")
print(f"Spectral Entropy final = {final_SE:.6e}")

# --- save CSV ---
import csv
with CSV_FILE.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["t", "E", "psi", "kappa", "psi_kappa", "SpectralEntropy"])
    for i in range(steps):
        w.writerow([t[i], energy[i], psi[i], kappa[i], psi_kappa[i], spectral_entropy[i]])

# --- plot ---
plt.figure(figsize=(8,4))
plt.plot(t, psi, label="ψ (quantum field)", alpha=0.7)
plt.plot(t, kappa, label="κ (curvature)", alpha=0.7)
plt.plot(t, psi_kappa, label="ψ*κ coupling", alpha=0.7)
plt.xlabel("Time")
plt.ylabel("Amplitude / Coupling")
plt.title("Test G9 - Emergent Gravity-Quantum Coupling")
plt.legend()
plt.tight_layout()
plt.savefig(PLOT_FILE, dpi=160)
plt.close()

# --- summary JSON ---
summary = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "mean_E": final_E,
    "mean_psi_kappa": final_PK,
    "mean_entropy": final_SE,
    "steps": steps,
    "source_csv": str(CSV_FILE.relative_to(REPO))
}
with JSON_FILE.open("w") as f:
    json.dump(summary, f, indent=2)

print(f"✅ Output written -> {CSV_FILE}")
print(f"🧾 Summary saved -> {JSON_FILE}")
print("----------------------------------------------------------")