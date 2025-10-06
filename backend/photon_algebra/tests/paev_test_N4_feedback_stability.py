# PAEV — N4: Entanglement Feedback Stability
# Repeated coupling pulses; track mutual-info gain per cycle and stability.
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# -------------------- config --------------------
CONST_PATH = Path("backend/modules/knowledge/constants_v1.1.json")
OUT_MI = "PAEV_N4_MutualInfo_Cycles.png"
OUT_GAIN = "PAEV_N4_CycleGain.png"
OUT_SUMMARY = "backend/modules/knowledge/N4_feedback_summary.json"

# time grid
T = 12.0          # total sim time
DT = 0.02
N = int(T/DT)
t = np.linspace(0, T, N, endpoint=False)

# two-well geometry (synthetic but consistent with M-series)
x = np.linspace(-5, 5, 200)
y = np.linspace(-5, 5, 200)
X, Y = np.meshgrid(x, y, indexing="xy")
r1 = np.sqrt((X+1.6)**2 + Y**2)
r2 = np.sqrt((X-1.6)**2 + Y**2)
kappa1 = -1.1/(r1+0.2)
kappa2 = -1.1/(r2+0.2)

# -------------------- helpers --------------------
def load_constants(path: Path):
    data = json.loads(path.read_text())
    return float(data["ħ_eff"]), float(data["G_eff"]), float(data["Λ_eff"]), float(data["α_eff"])

def mutual_info_proxy(psi1: np.ndarray, psi2: np.ndarray) -> float:
    # bounded proxy in [0, 1]: |corr| normalized by norms
    num = np.abs(np.vdot(psi1.ravel(), psi2.ravel()))
    den = np.linalg.norm(psi1) * np.linalg.norm(psi2) + 1e-12
    return float(np.clip(num/den, 0.0, 1.0))

def coupling_schedule(t_array: np.ndarray, alpha0: float, cycles: list[tuple[float,float,float]]):
    """
    cycles: list of (t_start, duration, gain) — gain multiplies alpha0
    returns α(t) with Gaussian window per pulse for smoothness.
    """
    a = np.full_like(t_array, alpha0, dtype=float)
    for t0, dur, gain in cycles:
        center = t0 + 0.5*dur
        sigma = 0.25*dur
        window = np.exp(-0.5*((t_array-center)/max(sigma,1e-6))**2)
        a += (gain*alpha0 - alpha0) * window
    return a

# -------------------- main sim --------------------
if __name__ == "__main__":
    ħ, G, Λ, α0 = load_constants(CONST_PATH)

    # initial entangled pair (phase-correlated Gaussians)
    psi1 = np.exp(-((X+1.6)**2 + Y**2)) * np.exp(1j*0.3*X)
    psi2 = np.exp(-((X-1.6)**2 + Y**2)) * np.exp(-1j*0.3*X)

    # cycle plan: three pulses; middle slightly stronger to test amplification
    # (t_start, duration, gain-multiplier on alpha0)
    cycles = [
        (2.0, 1.0, 1.10),
        (5.0, 1.2, 1.18),
        (8.2, 1.0, 1.12),
    ]
    alpha_t = coupling_schedule(t, α0, cycles)

    mi_series = []
    cycle_marks = []
    leakage_series = []

    # simple split-step update (qualitative proxy, consistent with earlier N-tests)
    for i in range(N):
        a = alpha_t[i]

        # laplacian via FFT is overkill; keep a light finite-diff proxy on magnitudes
        def lap(z):
            return (np.roll(z,1,0)+np.roll(z,-1,0)+np.roll(z,1,1)+np.roll(z,-1,1) - 4*z)

        # evolutions (skew-hermitian quantum term + curvature coupling + tiny dissipation)
        psi1 = psi1 + DT*(1j*ħ*lap(psi1) - a*kappa1*psi1) - 1e-4*psi1
        psi2 = psi2 + DT*(1j*ħ*lap(psi2) - a*kappa2*psi2) - 1e-4*psi2

        # renormalize softly to prevent numeric blowup
        for z in (psi1, psi2):
            nz = np.linalg.norm(z) + 1e-12
            z *= 1.0/nz

        mi_series.append(mutual_info_proxy(psi1, psi2))

        # crude “classical leakage” proxy: field flux between wells via gradient overlap
        g1x = np.gradient(np.abs(psi1), axis=1)
        g2x = np.gradient(np.abs(psi2), axis=1)
        leakage_series.append(float(np.mean(np.abs(g1x*g2x))))

        # remember cycle midpoints for plotting markers
        for t0, dur, _ in cycles:
            if abs(t[i] - (t0+0.5*dur)) < 0.5*DT:
                cycle_marks.append((i, mi_series[-1]))

    mi_series = np.array(mi_series)
    leakage_series = np.array(leakage_series)

    # compute per-cycle gains in mutual info around pulse centers
    gains = []
    centers = [t0+0.5*dur for (t0,dur,_) in cycles]
    halfw = int(0.25/DT)  # 0.25 time-window
    for c in centers:
        idx = int(c/DT)
        left = max(0, idx-halfw)
        right = min(N-1, idx+halfw)
        baseline = float(np.mean(mi_series[max(0,left-10):left])) if left > 0 else mi_series[0]
        peak = float(np.max(mi_series[left:right+1]))
        gains.append(max(peak - baseline, 0.0))

    gains = np.array(gains)
    # stability index: ratio of last-to-first gain (≈1 stable, >1 amplifying, <1 decaying)
    stability_index = float((gains[-1]+1e-12)/(gains[0]+1e-12))
    classification = (
        "Amplifying" if stability_index > 1.10 else
        "Decaying" if stability_index < 0.90 else
        "Stable"
    )

    # -------------------- plots --------------------
    plt.figure(figsize=(10,6))
    plt.plot(t, mi_series, label="Mutual Information I(ψ₁; ψ₂)")
    for (i, m) in cycle_marks:
        plt.axvline(t[i], ls="--", color="r", alpha=0.3)
    plt.xlabel("Time")
    plt.ylabel("I (normalized proxy)")
    plt.title("N4 — Mutual Information Across Feedback Cycles")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_MI, dpi=160)
    plt.close()

    plt.figure(figsize=(9,6))
    plt.bar(range(1, len(gains)+1), gains, width=0.6, label="Per-cycle MI gain")
    plt.axhline(np.mean(gains), ls="--", color="gray", alpha=0.6, label="Mean gain")
    plt.xlabel("Cycle #")
    plt.ylabel("ΔI per cycle")
    plt.title(f"N4 — Cycle Gain • Stability index={stability_index:.3f} ⇒ {classification}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_GAIN, dpi=160)
    plt.close()

    # -------------------- summary export --------------------
    OUT_SUMMARY_PATH = Path(OUT_SUMMARY)
    OUT_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "constants_path": str(CONST_PATH),
        "cycles": [{"t0": c[0], "duration": c[1], "gain_mult": c[2]} for c in cycles],
        "stability_index": stability_index,
        "classification": classification,
        "mean_leakage_proxy": float(np.mean(leakage_series)),
        "gains": gains.tolist(),
    }
    OUT_SUMMARY_PATH.write_text(json.dumps(summary, indent=2))

    print("=== N4 — Entanglement Feedback Stability ===")
    print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α₀={α0:.3f}")
    print(f"Cycle gains ΔI: {', '.join(f'{g:.3e}' for g in gains)}")
    print(f"Stability index = {stability_index:.3f}  ⇒  {classification}")
    print(f"Mean classical-leakage proxy = {np.mean(leakage_series):.3e}")
    print("✅ Plots saved:")
    print(f"   - {OUT_MI}")
    print(f"   - {OUT_GAIN}")
    print(f"📄 Summary: {OUT_SUMMARY}")