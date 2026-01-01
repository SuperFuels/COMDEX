import os, json, hashlib, subprocess
from pathlib import Path
from datetime import datetime, UTC

import numpy as np
import matplotlib.pyplot as plt

from backend.photon_algebra.utils.load_constants import load_constants


# ----------------------------
# Utilities
# ----------------------------
def utc_ts() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")

def git_rev() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"

def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a) + 1e-12)
    nb = float(np.linalg.norm(b) + 1e-12)
    return float(np.dot(a, b) / (na * nb))

def normalize_l2(x: np.ndarray) -> np.ndarray:
    return x / (np.linalg.norm(x) + 1e-12)

def find_weights_file() -> Path:
    # 1) explicit
    env = os.environ.get("WEIGHTS_PATH", "").strip()
    if env:
        p = Path(env)
        if p.exists() and p.is_file():
            return p
        raise FileNotFoundError(f"WEIGHTS_PATH set but not found: {p}")

    # 2) heuristic: pick the largest likely weight file in repo
    patterns = ("*.safetensors", "*.pth", "*.pt", "*.bin", "*.ckpt", "*.npz", "*.onnx")
    roots = [Path("."), Path("backend"), Path("models"), Path("weights"), Path("checkpoints")]
    candidates = []
    for r in roots:
        if not r.exists():
            continue
        for pat in patterns:
            candidates += list(r.rglob(pat))
    candidates = [p for p in candidates if p.is_file() and p.stat().st_size > 1024 * 128]

    if not candidates:
        raise FileNotFoundError(
            "No weight file found. Set WEIGHTS_PATH=/abs/or/relative/path/to/weights.(pth|pt|bin|safetensors|...)"
        )
    return max(candidates, key=lambda p: p.stat().st_size)

def load_repo_weights_as_glyphs(num_nodes: int) -> tuple[np.ndarray, str, str]:
    """
    Loads raw bytes from repo weight file, maps to 4 glyph bins (A,C,G,T) via byte%4,
    then maps to float levels for the lattice target vector.
    Returns (seq_float, file_sha256, file_path_str)
    """
    wfile = find_weights_file()
    raw = wfile.read_bytes()
    h = sha256_bytes(raw)

    # byte -> {0,1,2,3} -> float levels
    b = np.frombuffer(raw, dtype=np.uint8)
    g = (b % 4).astype(np.int32)
    levels = np.array([-1.0, -0.3333333, 0.3333333, 1.0], dtype=np.float64)
    seq = levels[g[:num_nodes]]

    seq = normalize_l2(seq.astype(np.float64))
    return seq, h, str(wfile)

def deterministic_ghost(num_nodes: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 100000)
    g = rng.integers(0, 4, size=num_nodes, endpoint=False)
    levels = np.array([-1.0, -0.3333333, 0.3333333, 1.0], dtype=np.float64)
    seq = levels[g].astype(np.float64)
    return normalize_l2(seq)

def tau_recovery_from_fidelity(f: np.ndarray, pulse_end: int, thresh: float, hold: int) -> int | None:
    # first index >= pulse_end where fidelity >= thresh for "hold" consecutive samples
    for i in range(pulse_end, len(f) - hold):
        if np.all(f[i:i+hold] >= thresh):
            return int(i - pulse_end)
    return None


# ----------------------------
# Core dynamics (simple, reviewer-proof)
# - diffusion + bounded corrective work (Obs_ON) + pulse noise
# - bounded correction penalizes high-frequency targets (structure can matter)
# ----------------------------
def simulate(
    target: np.ndarray,
    seed: int,
    obs_on: bool,
    dt: float,
    steps: int,
    pulse_start: int,
    pulse_dur: int,
    eta_pulse: float,
    k_diff: float,
    k_fb: float,
    k_obs: float,
    u_max: float,
) -> dict:
    rng = np.random.default_rng(seed)
    n = len(target)
    x = target.copy()

    fidelity = np.zeros(steps, dtype=np.float64)
    W_env = 0.0
    W_fb = 0.0
    W_obs = 0.0

    pulse_end = pulse_start + pulse_dur

    for t in range(steps):
        # diffusion
        lap = np.roll(x, -1) + np.roll(x, 1) - 2.0 * x

        # bounded corrective channels (only if obs_on)
        err = target - x
        fb_u = np.clip(k_fb * err, -u_max, u_max) if obs_on else 0.0 * err
        ob_u = np.clip(k_obs * err, -u_max, u_max) if obs_on else 0.0 * err

        # pulse noise (only during pulse window)
        if pulse_start <= t < pulse_end:
            noise = rng.normal(0.0, eta_pulse, size=n)
            W_env += float(np.sum(noise * noise))
        else:
            noise = 0.0

        # integrate
        x = x + dt * (k_diff * lap + fb_u + ob_u) + noise

        # bookkeeping
        W_fb += float(np.sum(np.asarray(fb_u) * np.asarray(fb_u)))
        W_obs += float(np.sum(np.asarray(ob_u) * np.asarray(ob_u)))

        fidelity[t] = cosine_similarity(x, target)

    return {
        "fidelity": fidelity,
        "summary": {
            "auc": float(np.mean(fidelity)),
            "tau_recovery_steps": tau_recovery_from_fidelity(
                fidelity, pulse_end, thresh=0.90, hold=50
            ),
            "W_env_pulse": float(W_env),
            "W_feedback": float(W_fb),
            "W_observer": float(W_obs),
            "W_total": float(W_env + W_fb + W_obs),
        },
    }


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # params (aligned to your declared schema)
    genome_len = 1024
    dt = 0.01
    steps = 4000
    seeds = [42, 43, 44, 45, 46]

    pulse_start = 1000
    pulse_dur = 50
    eta_pulse = 0.5

    # dynamics knobs
    k_diff = 2.0
    k_fb = 2.5
    k_obs = 1.0
    u_max = 0.015  # bounded correction => structure can matter

    # run id pinned in output (can be post-edited like you did with jq)
    run_id = f"P4s{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P4s"

    # load repo genome
    repo_seq, repo_sha, repo_path = load_repo_weights_as_glyphs(genome_len)

    conditions = [
        ("Repo_Obs_ON",  True,  "repo"),
        ("Repo_Obs_OFF", False, "repo"),
        ("Ghost_Obs_ON", True,  "ghost"),
        ("Ghost_Obs_OFF",False, "ghost"),
    ]

    per_condition = {}
    median_traces = {}

    for name, obs_on, kind in conditions:
        per_seed = {}
        traces = []
        for s in seeds:
            target = repo_seq if kind == "repo" else deterministic_ghost(genome_len, s)
            sim = simulate(
                target=target,
                seed=s,
                obs_on=obs_on,
                dt=dt,
                steps=steps,
                pulse_start=pulse_start,
                pulse_dur=pulse_dur,
                eta_pulse=eta_pulse,
                k_diff=k_diff,
                k_fb=k_fb,
                k_obs=k_obs,
                u_max=u_max,
            )
            per_seed[str(s)] = {
                "sequence_type": kind,
                "sequence_hash": repo_sha if kind == "repo" else None,
                "summary": sim["summary"],
            }
            traces.append(sim["fidelity"])

        traces = np.stack(traces, axis=0)
        med = np.median(traces, axis=0)
        median_traces[name] = med

        # aggregate stats
        aucs = [per_seed[str(s)]["summary"]["auc"] for s in seeds]
        Ws = [per_seed[str(s)]["summary"]["W_total"] for s in seeds]
        taus = [per_seed[str(s)]["summary"]["tau_recovery_steps"] for s in seeds]

        def iqr(vals):
            v = np.array([x for x in vals if x is not None], dtype=np.float64)
            if v.size == 0:
                return [None, None]
            return [float(np.percentile(v, 25)), float(np.percentile(v, 75))]

        tau_vals = [t for t in taus if t is not None]
        per_condition[name] = {
            "aggregate": {
                "auc_median": float(np.median(aucs)),
                "auc_iqr": [float(np.percentile(aucs, 25)), float(np.percentile(aucs, 75))],
                "tau_median_steps": (int(np.median(tau_vals)) if tau_vals else None),
                "tau_iqr_steps": iqr(taus),
                "W_total_median": float(np.median(Ws)),
                "W_total_iqr": [float(np.percentile(Ws, 25)), float(np.percentile(Ws, 75))],
            },
            "per_seed": per_seed,
        }

    # --- plots (median over seeds)
    t = np.arange(steps) * dt
    pulse_t0 = pulse_start * dt
    pulse_t1 = (pulse_start + pulse_dur) * dt

    # Fidelity matrix
    plt.figure(figsize=(12, 6))
    for name in median_traces:
        plt.plot(t, median_traces[name], label=name)
    plt.axhline(0.90, linestyle="--", linewidth=2)
    plt.axvspan(pulse_t0, pulse_t1, alpha=0.15)
    plt.ylim(-0.05, 1.05)
    plt.title("P4s — Spark (repo weights) fidelity 2×2 (median over seeds)")
    plt.xlabel("time")
    plt.ylabel("fidelity (cosine similarity)")
    plt.legend(loc="lower left")
    p_fid = OUT_DIR / "PAEV_P4s_FidelityMatrix.png"
    plt.tight_layout()
    plt.savefig(p_fid, dpi=200)
    plt.close()

    # Work proxy compare (Obs_ON only)
    # approximate using medians for display
    repoW = per_condition["Repo_Obs_ON"]["aggregate"]["W_total_median"]
    ghostW = per_condition["Ghost_Obs_ON"]["aggregate"]["W_total_median"]
    plt.figure(figsize=(12, 5))
    plt.bar(["Repo_Obs_ON", "Ghost_Obs_ON"], [repoW, ghostW])
    plt.title("P4s — Work proxy (W_total median over seeds)")
    plt.ylabel("W_total (proxy)")
    p_w = OUT_DIR / "PAEV_P4s_WorkProxy.png"
    plt.tight_layout()
    plt.savefig(p_w, dpi=200)
    plt.close()

    out = {
        "timestamp": utc_ts(),
        "run_id": run_id,
        "git_rev": git_rev(),
        "constants": const,
        "params": {
            "lattice_size": genome_len,
            "dt": dt,
            "steps_total": steps,
            "genome_len": genome_len,
            "seed_list": seeds,
            "pulse": {
                "enabled": True,
                "start_step": pulse_start,
                "duration_steps": pulse_dur,
                "eta_pulse": eta_pulse,
                "target": "genome_window",
                "profile": "gaussian_noise",
            },
            "fidelity": {
                "metric": "cosine_similarity",
                "threshold": 0.90,
                "hold_window_steps": 50,
            },
            "auc": {
                "definition": "mean_fidelity_over_steps",
                "window": {"start_step": 0, "end_step": steps},
            },
            "repo_weights": {
                "path": repo_path,
                "sha256": repo_sha,
            },
            "dynamics": {
                "k_diff": k_diff,
                "k_fb": k_fb,
                "k_obs": k_obs,
                "u_max": u_max,
            },
        },
        "definitions": {
            "tau_recovery": "first step after pulse_end where fidelity >= threshold for hold_window_steps consecutively",
            "W_p": {
                "meaning": "model-scoped work proxy for maintaining pattern under noise",
                "components": {
                    "W_env_pulse": "sum over pulse window of ||noise||^2 within genome window",
                    "W_feedback": "sum over all steps of ||feedback_update||^2 within genome window",
                    "W_observer": "sum over all steps of ||observer_update||^2 within genome window",
                    "W_total": "W_env_pulse + W_feedback + W_observer",
                },
            },
        },
        "conditions": per_condition,
        "files": {
            "fidelity_plot": str(p_fid.name),
            "work_plot": str(p_w.name),
        },
    }

    out_json = OUT_DIR / "P4s_spark_repo_weights.json"
    out_json.write_text(json.dumps(out, indent=2))
    print("=== P4s — Spark (repo weights) ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_fid}")
    print(f"✅ PNG  -> {p_w}")
    print(f"RUN_ID  -> {run_id}")


if __name__ == "__main__":
    main()
