import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

from backend.photon_algebra.utils.load_constants import load_constants

# =============================================================================
# P4x — Synthetic Genome Persistence & Resilience Battery (v0.4 style)
# - Pure numpy implementation (no tessaris.* API)
# - 2x2 matrix: {Genome,Ghost} x {Observer ON/OFF}
# - Pulse noise applied ONLY inside the genome window
# - Deterministic ghost per seed
# - L2 normalization for power-matching
# - Fidelity: cosine similarity vs injected patch
# - Work proxy W_p: env pulse + feedback update + observer update (model-scoped)
# - P4d induction: coupled vs decoupled neighbor control
# =============================================================================

OUT_DIR = Path("backend/modules/knowledge")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Parameters (reviewer-proof)
# -----------------------------
GENOME_LEN = 1024
LATTICE_SIZE = 1024
STEPS = 4000
DT = 0.01

SEEDS = [42, 43, 44, 45, 46]

PULSE_START = 1000
PULSE_DUR = 50
ETA_PULSE = 0.5  # 50% amplitude
PULSE_END = PULSE_START + PULSE_DUR

FID_THR = 0.90
HOLD_W = 50

# simple dynamics constants (kept explicit, model-scoped)
K_COUPLE = 0.06          # neighbor coupling strength
K_DAMP = 0.10            # damping toward 0 to prevent drift
K_FB_P = 0.20            # proportional feedback
K_FB_I = 0.02            # integral feedback
K_OBS = 0.25             # observer correction gain

EPS = 1e-12

def now_utc_stamp():
    # match style of existing tests (no timezone object)
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")

def l2_normalize(x: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(x))
    return x / (n + EPS)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(float)
    b = b.astype(float)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na < EPS or nb < EPS:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

def tau_recovery(fids: np.ndarray) -> int | None:
    # first step AFTER pulse_end where fid>=thr for HOLD_W consecutive steps
    start = PULSE_END
    if start + HOLD_W >= len(fids):
        return None
    good = fids >= FID_THR
    for t in range(start, len(fids) - HOLD_W):
        if bool(np.all(good[t:t+HOLD_W])):
            return t
    return None

def auc_mean_fidelity(fids: np.ndarray) -> float:
    return float(np.mean(fids))

def step_dynamics(x: np.ndarray) -> np.ndarray:
    # 1D laplacian (periodic) as "coupling"
    lap = np.roll(x, -1) - 2.0 * x + np.roll(x, 1)
    return x + K_COUPLE * lap - K_DAMP * x

def run_condition(seed: int, seq: np.ndarray, observer_on: bool, rng: np.random.Generator):
    # Lattice state
    x = np.zeros(LATTICE_SIZE, dtype=float)
    x[:] = seq[:]  # inject sequence into entire lattice window (len=1024)

    # integral for PI feedback
    I = np.zeros_like(x)

    # traces
    time = np.arange(STEPS, dtype=float) * DT
    fidelity = np.zeros(STEPS, dtype=float)
    pulse_mask = np.zeros(STEPS, dtype=int)

    # cumulative work proxies
    W_env_pulse_cum = np.zeros(STEPS, dtype=float)
    W_feedback_cum = np.zeros(STEPS, dtype=float)
    W_observer_cum = np.zeros(STEPS, dtype=float)
    W_total_cum = np.zeros(STEPS, dtype=float)

    W_env = 0.0
    W_fb = 0.0
    W_obs = 0.0

    for t in range(STEPS):
        # dynamics
        x_next = step_dynamics(x)

        # error vs injected patch
        e = (seq - x_next)

        # feedback update (always present: environment "controller")
        I = I + e * DT
        fb_update = (K_FB_P * e) + (K_FB_I * I)
        x_next = x_next + fb_update
        W_fb += float(np.sum(fb_update * fb_update))

        # observer update (only if enabled)
        obs_update = np.zeros_like(x_next)
        if observer_on:
            obs_update = K_OBS * e
            x_next = x_next + obs_update
            W_obs += float(np.sum(obs_update * obs_update))

        # pulse noise (only in genome window, which is the full vector here)
        if PULSE_START <= t < PULSE_END:
            pulse_mask[t] = 1
            noise = rng.normal(loc=0.0, scale=ETA_PULSE, size=LATTICE_SIZE)
            x_next = x_next + noise
            W_env += float(np.sum(noise * noise))

        # fidelity (cosine similarity to injected patch)
        fidelity[t] = cosine_similarity(x_next, seq)

        # cumulative work
        W_env_pulse_cum[t] = W_env
        W_feedback_cum[t] = W_fb
        W_observer_cum[t] = W_obs
        W_total_cum[t] = W_env + W_fb + W_obs

        x = x_next

    out = {
        "summary": {
            "auc": auc_mean_fidelity(fidelity),
            "tau_recovery_steps": tau_recovery(fidelity),
            "W_env_pulse": W_env,
            "W_feedback": W_fb,
            "W_observer": W_obs,
            "W_total": W_env + W_fb + W_obs
        },
        "trace": {
            "time": time.tolist(),
            "fidelity": fidelity.tolist(),
            "pulse_mask": pulse_mask.tolist(),
            "W_env_pulse_cum": W_env_pulse_cum.tolist(),
            "W_feedback_cum": W_feedback_cum.tolist(),
            "W_observer_cum": W_observer_cum.tolist(),
            "W_total_cum": W_total_cum.tolist(),
        }
    }
    return out

def summarize_aggregate(per_seed: dict):
    aucs = np.array([per_seed[str(s)]["summary"]["auc"] for s in SEEDS], dtype=float)
    taus = [per_seed[str(s)]["summary"]["tau_recovery_steps"] for s in SEEDS]
    Wtot = np.array([per_seed[str(s)]["summary"]["W_total"] for s in SEEDS], dtype=float)

    def iqr(x: np.ndarray):
        q1 = float(np.quantile(x, 0.25))
        q3 = float(np.quantile(x, 0.75))
        return [q1, q3]

    # taus can be None; compute median/IQR on finite only
    taus_f = np.array([t for t in taus if t is not None], dtype=float)
    if len(taus_f) == 0:
        tau_med = None
        tau_iqr = [None, None]
    else:
        tau_med = float(np.median(taus_f))
        tau_iqr = iqr(taus_f)

    return {
        "auc_median": float(np.median(aucs)),
        "auc_iqr": iqr(aucs),
        "tau_median_steps": tau_med,
        "tau_iqr_steps": tau_iqr,
        "W_total_median": float(np.median(Wtot)),
        "W_total_iqr": iqr(Wtot)
    }

def run_induction(seed: int, genome: np.ndarray, coupled: bool):
    # 2048 lattice: parent [0:1024], neighbor [1024:2048]
    N = 2048
    parent0 = 0
    neigh0 = 1024
    steps = 2000

    rng = np.random.default_rng(seed + 200000)

    x = np.zeros(N, dtype=float)
    x[parent0:parent0+GENOME_LEN] = genome
    x[neigh0:neigh0+GENOME_LEN] = 0.0

    # coupling mask: if decoupled, block interactions across the boundary
    # Implement by zeroing the laplacian terms that would mix indices 1023<->1024
    fidelity_neighbor = np.zeros(steps, dtype=float)

    for t in range(steps):
        x_next = x.copy()

        # laplacian update
        lap = np.roll(x, -1) - 2.0 * x + np.roll(x, 1)

        if not coupled:
            # remove cross-boundary mixing by zeroing lap at the two boundary indices
            lap[GENOME_LEN-1] = 0.0
            lap[GENOME_LEN] = 0.0

        x_next = x + K_COUPLE * lap - K_DAMP * x

        # small background noise to avoid trivial freezing
        x_next += rng.normal(0.0, 0.01, size=N)

        # neighbor fidelity to parent genome (cosine similarity)
        neighbor = x_next[neigh0:neigh0+GENOME_LEN]
        fidelity_neighbor[t] = cosine_similarity(neighbor, genome)

        x = x_next

    auc = float(np.mean(fidelity_neighbor))
    Fmax = float(np.max(fidelity_neighbor))

    return {
        "fidelity_neighbor_to_parent": fidelity_neighbor.tolist(),
        "F_i_max": Fmax,
        "auc_neighbor": auc
    }

def main():
    constants = load_constants()

    # "genome" (deterministic base sequence for the suite)
    # Use a fixed seed so the GENOME is stable across machines for v0.4
    genome_rng = np.random.default_rng(12345)
    genome = genome_rng.standard_normal(GENOME_LEN).astype(float)
    genome = l2_normalize(genome)

    results = {}
    schema_conditions = {}

    condition_specs = [
        ("Genome_Obs_ON",  True,  "genome"),
        ("Genome_Obs_OFF", False, "genome"),
        ("Ghost_Obs_ON",   True,  "ghost"),
        ("Ghost_Obs_OFF",  False, "ghost"),
    ]

    # run 2x2 matrix
    for name, obs_on, seq_type in condition_specs:
        per_seed = {}
        for seed in SEEDS:
            rng = np.random.default_rng(seed)

            if seq_type == "genome":
                seq = genome.copy()
            else:
                ghost_rng = np.random.default_rng(seed + 100000)
                ghost = ghost_rng.standard_normal(GENOME_LEN).astype(float)
                seq = l2_normalize(ghost)

            run = run_condition(seed=seed, seq=seq, observer_on=obs_on, rng=rng)

            # hash the injected sequence for audit
            seq_hash = "sha256:" + __import__("hashlib").sha256(seq.tobytes()).hexdigest()

            per_seed[str(seed)] = {
                "sequence_type": seq_type,
                "sequence_hash": seq_hash,
                "trace": run["trace"],
                "summary": run["summary"]
            }

        schema_conditions[name] = {
            "aggregate": summarize_aggregate(per_seed),
            "per_seed": per_seed
        }

    # run induction control (coupled vs decoupled)
    ind_coupled = run_induction(seed=42, genome=genome, coupled=True)
    ind_decoupled = run_induction(seed=42, genome=genome, coupled=False)

    schema_conditions["P4d_induction"] = {
        "params": {"lattice_size": 2048, "parent_offset": 0, "neighbor_offset": 1024, "steps": 2000},
        "controls": {"decoupled_neighbor": True},
        "results": {
            "coupled": ind_coupled,
            "decoupled": ind_decoupled
        }
    }

    # top-level schema output (matches your requested structure)
    out = {
        "timestamp": now_utc_stamp(),
        "run_id": "P4x_synthetic_genome_battery",
        "git_rev": (Path(".git/HEAD").read_text().strip() if Path(".git/HEAD").exists() else "UNKNOWN"),
        "constants": {
            "ħ": float(constants.get("ħ", 0.001)),
            "G": float(constants.get("G", 1e-5)),
            "Λ": float(constants.get("Λ", 1e-6)),
            "α": float(constants.get("α", 0.5)),
            "β": float(constants.get("β", 0.2)),
            "χ": 1.0
        },
        "params": {
            "lattice_size": LATTICE_SIZE,
            "dt": DT,
            "steps_total": STEPS,
            "genome_len": GENOME_LEN,
            "seed_list": SEEDS,
            "pulse": {
                "enabled": True,
                "start_step": PULSE_START,
                "duration_steps": PULSE_DUR,
                "eta_pulse": ETA_PULSE,
                "target": "genome_window",
                "profile": "gaussian_noise"
            },
            "fidelity": {
                "metric": "cosine_similarity",
                "threshold": FID_THR,
                "hold_window_steps": HOLD_W
            },
            "auc": {
                "definition": "mean_fidelity_over_steps",
                "window": {"start_step": 0, "end_step": STEPS}
            }
        },
        "definitions": {
            "tau_recovery": "first step after pulse_end where fidelity >= threshold for hold_window_steps consecutively",
            "W_p": {
                "meaning": "model-scoped work proxy for maintaining pattern under noise",
                "components": {
                    "W_env_pulse": "sum over pulse window of ||noise||^2 within genome window",
                    "W_feedback": "sum over all steps of ||feedback_update||^2 within genome window",
                    "W_observer": "sum over all steps of ||observer_update||^2 within genome window",
                    "W_total": "W_env_pulse + W_feedback + W_observer"
                }
            }
        },
        "conditions": schema_conditions,
        "files": {
            "json": "P4x_synthetic_genome_battery.json",
            "fig_fidelity": "PAEV_P4x_FidelityMatrix.png",
            "fig_work": "PAEV_P4x_WorkProxy.png",
            "fig_induction": "PAEV_P4x_Induction.png"
        }
    }

    # -----------------------------
    # Plots (v0.4 style)
    # -----------------------------
    def median_trace(cond_name: str, key: str):
        traces = [np.array(schema_conditions[cond_name]["per_seed"][str(s)]["trace"][key], dtype=float) for s in SEEDS]
        return np.median(np.stack(traces, axis=0), axis=0)

    t = np.array(schema_conditions["Genome_Obs_ON"]["per_seed"][str(SEEDS[0])]["trace"]["time"], dtype=float)

    # Fidelity matrix
    plt.figure(figsize=(10, 6))
    for cname in ["Genome_Obs_ON", "Genome_Obs_OFF", "Ghost_Obs_ON", "Ghost_Obs_OFF"]:
        plt.plot(t, median_trace(cname, "fidelity"), label=cname)
    plt.axvspan(PULSE_START*DT, PULSE_END*DT, alpha=0.2)
    plt.axhline(FID_THR, linestyle="--")
    plt.title("P4x — Fidelity (cosine similarity) 2×2 Matrix (median over seeds)")
    plt.xlabel("time")
    plt.ylabel("fidelity")
    plt.legend()
    fig1 = OUT_DIR / "PAEV_P4x_FidelityMatrix.png"
    plt.tight_layout()
    plt.savefig(fig1, dpi=180)
    plt.close()

    # Work proxy (cumulative)
    plt.figure(figsize=(10, 6))
    plt.plot(t, median_trace("Genome_Obs_ON", "W_total_cum"), label="Genome_Obs_ON W_total_cum")
    plt.plot(t, median_trace("Ghost_Obs_ON", "W_total_cum"), label="Ghost_Obs_ON W_total_cum")
    plt.axvspan(PULSE_START*DT, PULSE_END*DT, alpha=0.2)
    plt.title("P4x — Work Proxy (cumulative) comparison")
    plt.xlabel("time")
    plt.ylabel("W_total_cum")
    plt.legend()
    fig2 = OUT_DIR / "PAEV_P4x_WorkProxy.png"
    plt.tight_layout()
    plt.savefig(fig2, dpi=180)
    plt.close()

    # Induction (coupled vs decoupled)
    plt.figure(figsize=(10, 6))
    fc = np.array(ind_coupled["fidelity_neighbor_to_parent"], dtype=float)
    fd = np.array(ind_decoupled["fidelity_neighbor_to_parent"], dtype=float)
    tt = np.arange(len(fc)) * DT
    plt.plot(tt, fc, label=f"coupled (auc={ind_coupled['auc_neighbor']:.3f}, Fmax={ind_coupled['F_i_max']:.3f})")
    plt.plot(tt, fd, label=f"decoupled (auc={ind_decoupled['auc_neighbor']:.3f}, Fmax={ind_decoupled['F_i_max']:.3f})")
    plt.title("P4x — Induction control (neighbor fidelity to parent)")
    plt.xlabel("time")
    plt.ylabel("neighbor fidelity")
    plt.legend()
    fig3 = OUT_DIR / "PAEV_P4x_Induction.png"
    plt.tight_layout()
    plt.savefig(fig3, dpi=180)
    plt.close()

    # write JSON
    out_path = OUT_DIR / "P4x_synthetic_genome_battery.json"
    with out_path.open("w") as f:
        json.dump(out, f, indent=2)

    print("=== P4x — Synthetic Genome Battery ===")
    print(f"✅ JSON -> {out_path}")
    print(f"✅ PNG  -> {fig1}")
    print(f"✅ PNG  -> {fig2}")
    print(f"✅ PNG  -> {fig3}")

if __name__ == "__main__":
    main()
