# backend/photon_algebra/tests/paev_test_N16_entropy_feedback.py
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

# ---------- utilities ----------
def load_constants():
    base = Path("backend/modules/knowledge")
    for fn in ["constants_v1.2.json", "constants_v1.1.json", "constants_v1.0.json"]:
        p = base / fn
        if p.exists():
            data = json.loads(p.read_text())
            # v1.2 format
            if "constants" in data:
                c = data["constants"]
                return float(c.get("ħ", 1e-3)), float(c.get("G", 1e-5)), float(c.get("Λ", 1e-6)), float(c.get("α", 0.5)), float(c.get("β", 0.2))
            # v1.1 style (flat)
            return float(data.get("ħ_eff", 1e-3)), float(data.get("G_eff", 1e-5)), float(data.get("Λ_eff", 1e-6)), float(data.get("α_eff", 0.5)), 0.2
    # fallback defaults
    return 1e-3, 1e-5, 1e-6, 0.5, 0.2

def trap_integrate(y, x):
    # prefer numpy.trapezoid if available (to avoid deprecation warnings)
    if hasattr(np, "trapezoid"):
        return np.trapezoid(y, x)
    return np.trapz(y, x)

# ---------- model ----------
def simulate_entropy_feedback(T_eff, alpha0, beta, steps=800, dt=0.01, seed=42):
    """
    Toy yet consistent model for entropy flow once thermal rephasing (N15) is active.
    S(t) evolves toward S_eq with a feedback term from thermal phase error,
    plus small noise to reflect finite precision.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(steps) * dt

    # Effective targets based on thermal rephasing regime
    S_eq = 1.0 + 0.15 * np.tanh(1e-21 * T_eff)      # equilibrium entropy level
    phi_err0 = -0.6                                  # from N15 typical mean phase error ~ -0.61
    # Feedback gains: stronger rephasing reduces |phi_err| and dS/dt magnitude
    k_relax = 0.35 + 0.1 * alpha0
    k_fb    = 0.25 + 0.3 * beta

    # initialize
    S = np.zeros_like(t)
    S[0] = S_eq + 0.4   # start a bit above equilibrium
    phi_err = np.zeros_like(t)
    phi_err[0] = phi_err0

    # small stochasticity scaled by temperature (kept very small to be stable)
    sigma_S  = 2e-4
    sigma_ph = 2e-4

    for i in range(1, len(t)):
        # phase error relaxes with feedback (toward 0)
        dphi = -k_fb * phi_err[i-1] * dt + sigma_ph * rng.standard_normal()
        phi_err[i] = phi_err[i-1] + dphi

        # entropy relaxes toward S_eq with a correction proportional to |phi_err|
        dS = -k_relax * (S[i-1] - S_eq) * dt - 0.15 * phi_err[i] * dt + sigma_S * rng.standard_normal()
        S[i] = S[i-1] + dS

    # compute derivatives (finite diff)
    dS_dt = np.gradient(S, dt)
    return t, S, dS_dt, phi_err, S_eq

def classify_entropy_flow(dS_dt, t, window_frac=0.25, thr=1e-3):
    """
    Look at the last window of the run:
    - mean(dS/dt) < -thr  => 'Reversed' (entropy decreasing)
    - |mean(dS/dt)| <= thr => 'Balanced'
    - mean(dS/dt) >  thr  => 'Divergent'
    """
    n = len(t)
    w0 = int((1.0 - window_frac) * n)
    mean_tail = float(np.mean(dS_dt[w0:]))
    if mean_tail < -thr:
        return "Reversed", mean_tail
    if abs(mean_tail) <= thr:
        return "Balanced", mean_tail
    return "Divergent", mean_tail

# ---------- main ----------
def main():
    ħ, G, Λ, α, β = load_constants()
    # Effective temperature: reuse N8 scaling as heuristic (proportional to sqrt(Λ)/ħ)
    T_eff = (np.sqrt(max(Λ,1e-18)) / max(ħ,1e-12)) * 1e-3 * 1.0e21  # produce ~1e18–1e19 K scale

    t, S, dS_dt, phi_err, S_eq = simulate_entropy_feedback(T_eff, α, β, steps=1200, dt=0.01, seed=1337)
    cls, mean_tail = classify_entropy_flow(dS_dt, t, window_frac=0.3, thr=2e-3)

    print("=== N16 — Entropy Feedback Channel Test ===")
    print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}, β={β:.2f}")
    print(f"Effective T ≈ {T_eff:.3e} K")
    print(f"Mean dS/dt (tail) = {mean_tail:.3e}")
    print(f"Classification: {cls}")

    # --- plots ---
    # 1) Entropy vs time
    plt.figure(figsize=(8,4.5))
    plt.plot(t, S, lw=2)
    plt.axhline(S_eq, ls="--", alpha=0.6, label="S_eq")
    plt.xlabel("time")
    plt.ylabel("Entropy S(t)")
    plt.title("N16 — Entropy vs Time (Feedback Active)")
    plt.legend()
    out1 = Path("PAEV_N16_EntropyFeedback.png")
    plt.tight_layout()
    plt.savefig(out1, dpi=140)
    plt.close()

    # 2) dS/dt vs time
    plt.figure(figsize=(8,4.5))
    plt.plot(t, dS_dt, lw=1.8)
    plt.axhline(0.0, color="k", alpha=0.4, lw=1)
    plt.xlabel("time")
    plt.ylabel("dS/dt")
    plt.title("N16 — Entropy Flow (dS/dt)")
    out2 = Path("PAEV_N16_EntropyFlow.png")
    plt.tight_layout()
    plt.savefig(out2, dpi=140)
    plt.close()

    # --- summary JSON ---
    summary = {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
        "T_eff": T_eff,
        "S_eq": float(S_eq),
        "mean_dSdt_tail": float(mean_tail),
        "classification": cls,
        "files": {
            "entropy_plot": str(out1),
            "flow_plot": str(out2),
        },
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    }
    out_json = Path("backend/modules/knowledge/N16_entropy_feedback.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2))

    print("✅ Plots saved:")
    print(f"   - {out1}")
    print(f"   - {out2}")
    print(f"📄 Summary: {out_json}")

if __name__ == "__main__":
    main()