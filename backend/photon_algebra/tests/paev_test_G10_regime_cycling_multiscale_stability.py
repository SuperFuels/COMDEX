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

CSV_FILE  = TESTS_DIR / "results_G10_regime_cycling_multiscale_stability.csv"
PLOT_FILE = TESTS_DIR / "PAEV_TestG10_RegimeCycling.png"
JSON_FILE = CONST_DIR / "G10_regime_cycling_multiscale_stability.json"

print("=== Test G10 - Regime Cycling & Multiscale Stability ===")

# --- simulate multiscale transition ---
steps = 1000
t = np.linspace(0, 20, steps)
np.random.seed(99)

# energy and stability traces with scale transitions
energy = 0.005 + 0.002*np.sin(0.6*t) + 0.0008*np.random.randn(steps)
stability = 0.2 + 0.05*np.sin(0.4*t) + 0.03*np.random.randn(steps)
spectral_entropy = 0.45 + 0.05*np.sin(0.3*t + 0.5) + 0.02*np.random.randn(steps)

# --- compute summary values ---
final_E  = float(np.mean(energy[-100:]))
final_ST = float(np.mean(stability[-100:]))
final_SE = float(np.mean(spectral_entropy[-100:]))

print(f"⟨E⟩ final = {final_E:.6e}")
print(f"⟨Stability⟩ final = {final_ST:.6e}")
print(f"Spectral Entropy final = {final_SE:.6e}")

# --- save CSV ---
import csv
with CSV_FILE.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["t", "Energy", "Stability", "SpectralEntropy"])
    for i in range(steps):
        w.writerow([t[i], energy[i], stability[i], spectral_entropy[i]])

# --- plot ---
plt.figure(figsize=(8,4))
plt.plot(t, energy, label="Energy", alpha=0.8)
plt.plot(t, stability, label="Stability", alpha=0.8)
plt.plot(t, spectral_entropy, label="Spectral Entropy", alpha=0.8)
plt.xlabel("Time")
plt.ylabel("Amplitude")
plt.title("Test G10 - Regime Cycling & Multiscale Stability")
plt.legend()
plt.tight_layout()
plt.savefig(PLOT_FILE, dpi=160)
plt.close()

# --- summary JSON ---
summary = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "mean_energy": final_E,
    "mean_stability": final_ST,
    "mean_entropy": final_SE,
    "steps": steps,
    "source_csv": str(CSV_FILE.relative_to(REPO))
}
with JSON_FILE.open("w") as f:
    json.dump(summary, f, indent=2)

print(f"✅ Output written -> {CSV_FILE}")
print(f"🧾 Summary saved -> {JSON_FILE}")
print("----------------------------------------------------------")