# backend/photon_algebra/tests/paev_test_P10m_lock_certification.py
# P10m — Global Lock Certification (stress sweeps + relock)
import json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone

np.random.seed(123)

# ----- Base model (from P10k/P10l lineage) -----
T = 1600
M = 3
eta = 1e-3

# Alignment / fusion block (nonlinear + bias)
ALIGN = dict(
    kappa_align_base = 0.06,
    kappa_boost      = 0.18,
    curvature_gain   = 0.20,
    phase_damp       = 0.022,
    merge_bias_gain  = 0.009,
    bias_gain        = 0.004,     # asymmetric nudge toward global mean
)

# Adaptive global order-parameter controller (simple clamp profile)
R_target = 0.992
K_global_min, K_global_max = 0.05, 0.30

# Re-lock test
PERT_T = 800
PERT_MAG = 0.015
LOCK_R_THRESH = 0.991
LOCK_PHI_THRESH = 0.06   # proxy using mean(|phi - global_mean|) tail

def complex_order_parameter(phivec):
    z = np.exp(1j * phivec)
    zb = z.mean()
    return abs(zb), np.angle(zb)

def simulate_once(seed, noise=0.0023, K_field=0.08, damping=0.04, leak=0.0085):
    rng = np.random.default_rng(seed)
    phi = np.zeros((M, T))
    # separated start (like P10 series)
    phi[:, 0] = np.array([0.0, 0.40, -0.25])
    omega = np.array([0.002, -0.001, 0.0005])

    K_global = K_global_min
    R_hist = np.zeros(T)
    Kg_hist = np.zeros(T)

    for t in range(1, T):
        R, psi = complex_order_parameter(phi[:, t-1])
        R_hist[t-1] = R

        # simple order-parameter clamp toward target
        # stronger when R<R_target, weaker when close/super-threshold
        Kg_step = 0.25*(R_target - R)
        K_global = np.clip(K_global + Kg_step, K_global_min, K_global_max)
        Kg_hist[t-1] = K_global

        # per-field phase update
        for i in range(M):
            # local field coupling (Kuramoto pairwise)
            local = 0.0
            for j in range(M):
                if j == i: continue
                local += np.sin(phi[j, t-1] - phi[i, t-1])
            local *= K_field / (M-1)

            # global pull to psi
            global_term = K_global * np.sin(psi - phi[i, t-1])

            # nonlinear “fusion” (curvature reduces large errors, saturates near lock)
            err = (psi - phi[i, t-1])
            err = np.arctan2(np.sin(err), np.cos(err))
            nonlin = ALIGN["curvature_gain"] * np.tanh(5.0*err)

            # alignment damper & slight merge bias toward psi
            align_damp = -ALIGN["phase_damp"] * phi[i, t-1]
            merge_bias = ALIGN["merge_bias_gain"] * err + ALIGN.get("bias_gain", 0.0)*err

            # noise
            xi = rng.normal(0.0, noise)

            dphi = (omega[i] + local + global_term + nonlin + align_damp + merge_bias
                    - damping*phi[i, t-1] - leak*phi[i, t-1] + xi)

            phi[i, t] = phi[i, t-1] + eta*dphi

        # single step perturbation after formation
        if t == PERT_T:
            phi[1, t:] += PERT_MAG

    # finalize histories
    R, psi = complex_order_parameter(phi[:, -1])
    R_hist[-1] = R
    Kg_hist[-1] = K_global

    # metrics (tail)
    tail = slice(int(0.8*T), None)
    R_tail = R_hist[tail]
    R_tail_mean = float(np.mean(R_tail))
    R_tail_slope = float(np.polyfit(np.arange(len(R_tail)), R_tail, 1)[0])

    # phase dispersion proxy (mean abs deviation from global mean)
    global_mean = np.unwrap(np.angle(np.exp(1j*phi).mean(axis=0)))
    tail_disp = float(np.mean(np.abs((phi[:, tail] - global_mean[tail]).reshape(-1))))

    lock_ratio_R = float(np.mean(R_tail > LOCK_R_THRESH))
    lock_ratio_phi = float(np.mean(np.abs((phi[:, tail] - global_mean[tail]).reshape(-1)) < LOCK_PHI_THRESH))

    # relock time: 95% of next 120 steps above threshold after perturb
    relock_time = None
    window = 120
    for t in range(PERT_T+5, T-window):
        seg = R_hist[t:t+window]
        if np.mean(seg > LOCK_R_THRESH) >= 0.95:
            relock_time = int(t - PERT_T)
            break

    return {
        "R_tail_mean": R_tail_mean,
        "R_tail_slope": R_tail_slope,
        "lock_ratio_R": lock_ratio_R,
        "lock_ratio_phi": lock_ratio_phi,
        "tail_mean_phase_error": tail_disp,
        "relock_time": relock_time,
        "R_hist": R_hist,
        "Kg_hist": Kg_hist,
    }

# ----- Sweep grid -----
noise_grid = [0.0020, 0.0023, 0.0026, 0.0030]
Kfield_grid = [0.06, 0.08, 0.10]
seeds = [11, 23, 37, 49, 61]  # multi-trial robustness

def passed(m):
    return (m["R_tail_mean"] >= 0.998 and
            m["lock_ratio_R"]  >= 0.95 and
            (m["relock_time"] is not None and m["relock_time"] <= 80) and
            abs(m["R_tail_slope"]) < 7e-06)

results_mat = np.zeros((len(noise_grid), len(Kfield_grid)))
best_example = None
best_key = None

all_records = []
for i, nz in enumerate(noise_grid):
    for j, kf in enumerate(Kfield_grid):
        passes = 0
        local_metrics = []
        for s in seeds:
            m = simulate_once(s, noise=nz, K_field=kf)
            local_metrics.append({
                "seed": s, "noise": nz, "K_field": kf,
                **{k:v for k,v in m.items() if k not in ("R_hist","Kg_hist")}
            })
            if passed(m):
                passes += 1
            # track best by (highest R_tail_mean, then lowest relock)
            if best_example is None or (m["R_tail_mean"] > best_example["R_tail_mean"] or
               (abs(m["R_tail_mean"]-best_example["R_tail_mean"]) < 1e-6 and
                (m["relock_time"] or 1e9) < (best_example.get("relock_time") or 1e9))):
                best_example = m
                best_key = (nz, kf, s)
        results_mat[i, j] = passes / len(seeds)
        all_records.extend(local_metrics)

# ----- Plots -----
plt.figure(figsize=(7.4, 4.6))
im = plt.imshow(results_mat, origin="lower", cmap="viridis",
                extent=[min(Kfield_grid)-0.005, max(Kfield_grid)+0.005,
                        min(noise_grid)-0.00005, max(noise_grid)+0.00005],
                aspect="auto", vmin=0, vmax=1)
plt.colorbar(im, label="pass rate")
plt.xticks(Kfield_grid); plt.yticks(noise_grid)
plt.xlabel("K_field"); plt.ylabel("noise"); plt.title("P10m — Global Lock Certification (pass rate)")
plt.tight_layout()
plt.savefig("PAEV_P10m_LockCertification_Heatmap.png")

# Example R(t) from best run
plt.figure(figsize=(8.6, 4.4))
plt.plot(best_example["R_hist"], label="R(t)")
plt.axhline(LOCK_R_THRESH, color="red", ls="--", alpha=0.6, label=f"lock R={LOCK_R_THRESH}")
plt.axvline(PERT_T, color="purple", ls="--", alpha=0.8, label="perturbation")
Kg_scaled = (best_example["Kg_hist"] - K_global_min) / max(1e-9, (K_global_max - K_global_min))
plt.plot(Kg_scaled, "k--", alpha=0.6, label="scaled K_global(t)")
plt.ylim(0.94, 1.005)
plt.title(f"P10m — Best Trial R(t)  (noise={best_key[0]:.4f}, K_field={best_key[1]:.2f}, seed={best_key[2]})")
plt.xlabel("time step"); plt.ylabel("Normalized value")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_P10m_BestTrial_R.png")

# ----- Save JSON -----
summary = {
    "eta": eta,
    "T": T,
    "grid": {"noise": noise_grid, "K_field": Kfield_grid, "seeds": seeds},
    "criteria": {
        "R_tail_mean >= 0.998": True,
        "lock_ratio_R >= 0.95": True,
        "relock_time <= 80": True,
        "|R_tail_slope| < 7e-6": True
    },
    "pass_rate_matrix": results_mat.tolist(),
    "best": {
        "noise": best_key[0], "K_field": best_key[1], "seed": best_key[2],
        "R_tail_mean": best_example["R_tail_mean"],
        "lock_ratio_R": best_example["lock_ratio_R"],
        "relock_time": best_example["relock_time"],
        "R_tail_slope": best_example["R_tail_slope"],
        "tail_mean_phase_error": best_example["tail_mean_phase_error"],
    },
    "alignment": ALIGN,
    "files": {
        "heatmap": "PAEV_P10m_LockCertification_Heatmap.png",
        "best_R":  "PAEV_P10m_BestTrial_R.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}
with open("backend/modules/knowledge/P10m_lock_certification.json", "w") as f:
    json.dump(summary, f, indent=2)

print("=== P10m — Global Lock Certification (stress sweeps) ===")
print(f"Grid pass rates (rows=noise, cols=K_field):")
print(np.array_str(results_mat, precision=2))
print(f"Best: noise={best_key[0]:.4f}, K_field={best_key[1]:.2f}, seed={best_key[2]} | "
      f"R_tail_mean={best_example['R_tail_mean']:.4f}, lock_R={best_example['lock_ratio_R']:.2f}, "
      f"relock={best_example['relock_time']}, slope={best_example['R_tail_slope']:.2e}")
print("✅ Results saved → backend/modules/knowledge/P10m_lock_certification.json")