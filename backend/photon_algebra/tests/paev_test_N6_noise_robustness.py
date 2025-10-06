# backend/photon_algebra/tests/paev_test_N6_noise_robustness.py
import json, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
np.random.seed(0)

C_PATH = Path("backend/modules/knowledge/constants_v1.1.json")
with C_PATH.open() as f:
    C = json.load(f)
ħ, G, Λ, α = C["ħ_eff"], C["G_eff"], C["Λ_eff"], C["α_eff"]

# Synthetic sender/receiver “bridge” signals
T = 2000
t = np.linspace(0, 10, T)
s_tx = np.exp(-0.5*((t-3.5)/0.8)**2) * np.cos(4*t)           # encoded pattern
s_rx_clean = np.exp(-0.5*((t-3.5)/0.8)**2) * np.cos(4*(t))   # ideal echo

sigmas = np.logspace(-5, -1, 21)   # noise std sweep
dephase = 0.03                     # phase jitter (rad) std

fids = []
for σ in sigmas:
    # add noise and random phase jitter (slow)
    jitter = np.cumsum(np.random.normal(0, dephase/np.sqrt(T), size=T))
    s_rx = s_rx_clean * np.cos(jitter) - 0 * np.sin(jitter)
    s_rx += np.random.normal(0, σ, size=T)

    # L2-normalized fidelity proxy |<rx|tx>|^2
    tx = s_tx/np.linalg.norm(s_tx)
    rx = s_rx/np.linalg.norm(s_rx)
    fids.append( float(np.abs(np.vdot(tx, rx))**2) )

fids = np.array(fids)
thr = 0.90
idx = np.where(fids>=thr)[0]
sigma_thr = sigmas[idx[-1]] if len(idx)>0 else np.nan

print("=== N6 — Noise Robustness ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")
print(f"90% fidelity noise threshold σ ≈ {sigma_thr:.3e}")

# Plot
plt.figure(figsize=(8,5))
plt.semilogx(sigmas, fids, lw=2)
plt.axhline(thr, ls="--", alpha=0.5, label="0.90 fidelity")
plt.xlabel("Noise σ"); plt.ylabel("Fidelity |⟨rx|tx⟩|²")
plt.title("N6 — Entanglement Transport Noise Robustness")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_N6_NoiseRobustness.png", dpi=160)

# Save summary
out = {
    "ħ":ħ,"G":G,"Λ":Λ,"α":α,
    "sigmas":sigmas.tolist(),
    "fidelities":fids.tolist(),
    "fidelity_threshold":thr,
    "sigma_at_90pct": None if np.isnan(sigma_thr) else float(sigma_thr),
}
Path("backend/modules/knowledge/N6_noise_summary.json").write_text(json.dumps(out, indent=2))
print("✅ Plots saved: PAEV_N6_NoiseRobustness.png")
print("📄 Summary: backend/modules/knowledge/N6_noise_summary.json")