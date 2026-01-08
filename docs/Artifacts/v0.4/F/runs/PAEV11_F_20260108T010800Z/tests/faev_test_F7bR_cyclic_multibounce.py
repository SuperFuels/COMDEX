import json, os, math
import numpy as np
import matplotlib.pyplot as plt

# ---------- Utilities ----------
def moving_avg(x, k=9):
    if k <= 1: return x
    pad = k//2
    xpad = np.pad(x, (pad, pad), mode="edge")
    c = np.cumsum(xpad)
    return (c[k:] - c[:-k]) / k

def detect_bounces(a, t):
    # bounce = local minimum of a(t): ȧ crosses 0 with a''>0
    adot = np.gradient(a, t)
    addot = np.gradient(adot, t)
    idx = []
    for i in range(1, len(t)-1):
        if adot[i-1] < 0 and adot[i+1] > 0 and addot[i] > 0:
            idx.append(i)
    return idx

# ---------- Model ----------
def run_sim(cfg):
    dt = cfg["dt"]; T = cfg["T"]
    N  = int(T/dt)+1
    t  = np.linspace(0, T, N)

    # Params (dual-field + LQC + controller)
    alpha=cfg["alpha"]; beta=cfg["beta"]
    kappa=cfg["kappa"]; omega0=cfg["omega0"]
    xi=cfg["xi"]; delta=cfg["delta"]; noise=cfg["noise"]
    rho_c=cfg["rho_c"]           # LQC critical density
    kp=cfg["kp"]; ki=cfg["ki"]; kd=cfg["kd"]
    g_couple=cfg["g_couple"]

    # New: cyclical assist near minima
    # weak sinusoid gated by window around bounces (constructed on-the-fly)
    lam_amp   = cfg["cycle"]["lam_amp"]          # ~ 1e-3 to 1e-2
    lam_omega = cfg["cycle"]["lam_omega"]        # period scale
    lam_gate_w= cfg["cycle"]["gate_width"]       # time window around a_min
    reinject  = cfg["cycle"]["reinject_frac"]    # 1-3% KE restore per bounce

    # State
    a  = np.zeros(N);  a[0]  = 1.0
    H  = np.zeros(N);  H[0]  = -cfg["H0"]  # start contracting
    phi1 = np.zeros(N); phid1 = np.zeros(N)
    phi2 = np.zeros(N); phid2 = np.zeros(N)
    # small initial displacements
    phi1[0]=0.02; phi2[0]=-0.018

    # Controller terms
    integ = 0.0; prev_err = 0.0

    # Logging
    rho_tot = np.zeros(N); rho_phi = np.zeros(N); lam_eff = np.zeros(N)
    entropy_flux = np.zeros(N)

    # helper potentials (soft-saturating)
    def V(phi):
        return 0.5*(omega0**2)*phi**2 + beta*phi**4/(1.0 + phi**2)
    def dV(phi):
        denom = (1.0 + phi**2)
        return (omega0**2)*phi + (4*beta*phi**3)/denom - (2*beta*phi**5)/(denom**2)

    # cycle timing (filled as we find minima)
    bounce_times = []

    for i in range(1, N):
        # energies
        rho1 = 0.5*phid1[i-1]**2 + V(phi1[i-1])
        rho2 = 0.5*phid2[i-1]**2 + V(phi2[i-1])
        # coupling term (small coherent spring)
        U12  = 0.5*g_couple*(phi1[i-1]-phi2[i-1])**2
        rho_phi[i-1] = rho1 + rho2 + U12

        # base vacuum (slow)
        Lambda_base = cfg["Lambda_base"]

        # weak cycle driver, gated near most recent bounce
        t_now = t[i-1]
        gate = 0.0
        if bounce_times:
            if abs(t_now - bounce_times[-1]) < lam_gate_w:
                gate = 1.0
        lam_drive = lam_amp*math.sin(lam_omega*t_now)*gate

        # PI-D control to anti-correlate with total energy (low-pass via mov.avg later)
        target = cfg["target_energy"]
        err = target - rho_phi[i-1]
        integ = np.clip(integ + err*dt, -0.1, 0.1)
        deriv = (err - prev_err)/dt
        prev_err = err
        lam_ctrl = kp*err + ki*integ + kd*deriv

        lam_eff[i-1] = max(0.0, Lambda_base + lam_ctrl + lam_drive)

        # LQC effective Friedmann: H^2 = (kappa/3) rho (1 - rho/rho_c) - Lambda/3
        rho_eff = rho_phi[i-1]
        H2 = (kappa/3.0)*rho_eff*(1.0 - rho_eff/max(rho_c,1e-9)) - lam_eff[i-1]/3.0
        H[i] = -math.sqrt(max(H2, 0.0)) if H[i-1] < 0 else math.sqrt(max(H2,0.0))

        # scalar dynamics with Hubble friction
        phidd1 = -3.0*H[i]*phid1[i-1] - dV(phi1[i-1]) - g_couple*(phi1[i-1]-phi2[i-1])
        phidd2 = -3.0*H[i]*phid2[i-1] - dV(phi2[i-1]) + g_couple*(phi1[i-1]-phi2[i-1])
        # small stochastic bath
        phidd1 += noise*np.random.randn()*math.sqrt(dt)
        phidd2 += noise*np.random.randn()*math.sqrt(dt)

        phid1[i] = phid1[i-1] + phidd1*dt
        phid2[i] = phid2[i-1] + phidd2*dt
        phi1[i]  = phi1[i-1]  + phid1[i]*dt
        phi2[i]  = phi2[i-1]  + phid2[i]*dt

        # scale update
        a[i] = max(1e-6, a[i-1] * (1.0 + H[i]*dt))
        rho_tot[i-1] = rho_eff

        # crude "information/entropy" flux: |d/dt ln coherence|
        coh = np.cos(phi1[i-1]-phi2[i-1])
        dcoh = (np.cos(phi1[i-1]-phi2[i-1]) - np.cos(phi1[i-2]-phi2[i-2]))/dt if i>1 else 0.0
        entropy_flux[i-1] = abs(dcoh)/(abs(coh)+1e-4)

        # bounce handling (we'll refine after loop once a[] known)

    # finalize last samples
    rho_tot[-1]=rho_tot[-2]; rho_phi[-1]=rho_phi[-2]; lam_eff[-1]=lam_eff[-2]
    entropy_flux[-1]=entropy_flux[-2]

    # detect bounces now that a(t) is complete
    b_idx = detect_bounces(a, t)
    for bi in b_idx:
        bounce_times.append(t[bi])
        # controller hygiene: clear bias
        integ = 0.0

        # reinject a small fraction of scalar KE to compensate dissipative losses
        ke = 0.5*(phid1[bi]**2 + phid2[bi]**2)
        boost = reinject*max(ke, 0.0)
        if boost > 0:
            # push symmetrically to preserve Δφ phase
            s = math.sqrt(2*boost)
            phid1[bi:] +=  0.5*s
            phid2[bi:] +=  0.5*s

    # recompute a quick post-injection smoothing of H to avoid spikes
    H_s = moving_avg(H, 5)

    return {
        "t": t.tolist(),
        "a": a.tolist(),
        "rho_tot": rho_tot.tolist(),
        "rho_phi": rho_phi.tolist(),
        "lambda_eff": lam_eff.tolist(),
        "entropy_flux": entropy_flux.tolist(),
        "bounces": [float(x) for x in bounce_times],
        "H": H_s.tolist()
    }

# ---------- Main ----------
if __name__ == "__main__":
    cfg = dict(
        dt=0.002, T=40.0,
        alpha=0.7, beta=0.08, kappa=0.065, omega0=0.18,
        xi=0.015, delta=0.05, noise=0.0005,
        rho_c=1.0, Lambda_base=0.0035,
        kp=0.18, ki=0.004, kd=0.03,
        g_couple=0.015,
        H0=-0.25,                      # stronger initial contraction
        target_energy=0.04,            # lower to trigger bounce
        cycle=dict(
            lam_amp=0.0016,            # stronger breathing drive
            lam_omega=1.0,             # oscillation frequency
            gate_width=0.4,
            reinject_frac=0.03         # small kinetic boost at bounce
        )
    )
    out = run_sim(cfg)
    t = np.array(out["t"]); a = np.array(out["a"])
    rho = np.array(out["rho_tot"]); lam = np.array(out["lambda_eff"])
    S = np.array(out["entropy_flux"]); bts = out["bounces"]

    # Metrics
    bcount = len(bts)
    coh = np.cos(np.array(moving_avg(np.zeros_like(t),1)))  # placeholder (not used here)
    mean_S = float(np.mean(S[int(0.1*len(S)):]))

    cls = "✅ Multi-bounce achieved" if bcount >= 2 else "⚠️ Single bounce"
    print(f"=== F7b-RC2 - Cyclic Multi-Bounce Test ===")
    print(f"bounces={bcount} | mean_entropy_flux={mean_S:.4g}")
    print(f"-> {cls}")

    # Plots
    plt.figure(figsize=(8,4.6))
    plt.plot(t, a, lw=2, label="a(t)")
    for bt in bts: plt.axvline(bt, ls="--", c="purple", alpha=0.6)
    plt.title("F7b-RC2 - Scale Factor (multi-bounce)")
    plt.xlabel("time"); plt.ylabel("a(t)"); plt.legend(); plt.tight_layout()
    plt.savefig("FAEV_F7bRC2_Scale.png", dpi=130)

    plt.figure(figsize=(8,4.6))
    plt.semilogy(t, rho, lw=1.8, label="ρ_total")
    plt.semilogy(t, lam, lw=1.4, ls="--", label="Λ_eff(t)")
    plt.title("F7b-RC2 - Energy & Λ_eff(t)")
    plt.xlabel("time"); plt.ylabel("energy (log)"); plt.legend(); plt.tight_layout()
    plt.savefig("FAEV_F7bRC2_Energy.png", dpi=130)

    plt.figure(figsize=(8,4.6))
    plt.plot(t, S, lw=1.5, c="crimson", label="entropy flux")
    for bt in bts: plt.axvline(bt, ls="--", c="gray", alpha=0.4)
    plt.title("F7b-RC2 - Entropy / Information Flux")
    plt.xlabel("time"); plt.ylabel("S(t)"); plt.legend(); plt.tight_layout()
    plt.savefig("FAEV_F7bRC2_Entropy.png", dpi=130)

    # Save knowledge record
    rec = {
        "config": cfg,
        "metrics": {
            "num_bounces": bcount,
            "mean_entropy_flux": mean_S
        },
        "files": {
            "scale_plot": "FAEV_F7bRC2_Scale.png",
            "energy_plot": "FAEV_F7bRC2_Energy.png",
            "entropy_plot": "FAEV_F7bRC2_Entropy.png"
        }
    }
    os.makedirs("backend/modules/knowledge", exist_ok=True)
    with open("backend/modules/knowledge/F7bRC2_cyclic_multibounce.json","w") as f:
        json.dump(rec, f, indent=2)