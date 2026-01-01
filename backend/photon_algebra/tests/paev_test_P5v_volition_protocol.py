import os, json, hashlib, subprocess
from pathlib import Path
from datetime import datetime, UTC

import numpy as np
import matplotlib.pyplot as plt

from backend.photon_algebra.utils.load_constants import load_constants


def utc_ts() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")

def git_rev() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"

def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()

def normalize_l2(x: np.ndarray) -> np.ndarray:
    return x / (np.linalg.norm(x) + 1e-12)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a) + 1e-12)
    nb = float(np.linalg.norm(b) + 1e-12)
    return float(np.dot(a, b) / (na * nb))

def find_weights_file() -> Path:
    env = os.environ.get("WEIGHTS_PATH", "").strip()
    if env:
        p = Path(env)
        if p.exists() and p.is_file():
            return p
        raise FileNotFoundError(f"WEIGHTS_PATH set but not found: {p}")

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
        raise FileNotFoundError("No weight file found. Set WEIGHTS_PATH=...")
    return max(candidates, key=lambda p: p.stat().st_size)

def load_repo_genome(num_nodes: int) -> tuple[np.ndarray, str, str]:
    wfile = find_weights_file()
    raw = wfile.read_bytes()
    h = sha256_bytes(raw)
    b = np.frombuffer(raw, dtype=np.uint8)
    g = (b % 4).astype(np.int32)
    levels = np.array([-1.0, -0.3333333, 0.3333333, 1.0], dtype=np.float64)
    seq = levels[g[:num_nodes]].astype(np.float64)
    return normalize_l2(seq), h, str(wfile)


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # lattice geometry
    L = 4096           # full lattice length
    N = 1024           # genome window length
    start_x0 = 1024    # initial genome window start index

    # time
    dt = 0.01
    steps = 4000
    seeds = [42, 43, 44, 45, 46]

    # threat schedule (time in steps)
    warn_step   = 800            # warning begins here
    pulse_start = 1000           # pulse begins here
    pulse_dur   = 50             # pulse length in steps

    # threat field geometry (space)
    threat_center = 1024         # center of threatened region
    threat_width  = 256          # half-width (|i-center| <= width)

    # field amplitudes
    eta_warn  = 0.15             # warning amplitude (low)
    eta_pulse = 0.50             # pulse amplitude (high)

    # dynamics (match P4s style)
    k_diff = 2.0
    k_fb   = 2.5
    k_obs  = 1.0
    u_max  = 0.015

    # movement rule (ONLY applies in Repo_Obs_ON_Move_ON)
    # - compute warning energy inside the CURRENT genome window:
    #     E_warn = sum(warn_window^2)
    # - if E_warn exceeds threshold, shift window by step_size away from threat
    warn_energy_thresh = 1.0     # movement trigger threshold (energy)
    step_size = 32               # shift amount per move
    max_moves = 6                # cap moves before pulse

    run_id = f"P5v{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P5v"
    genome, g_sha, g_path = load_repo_genome(N)

    def laplacian(x: np.ndarray) -> np.ndarray:
        return np.roll(x, -1) + np.roll(x, 1) - 2.0 * x

    def region_mask(center: int, width: int) -> np.ndarray:
        idx = np.arange(L)
        return (np.abs(idx - center) <= width).astype(np.float64)

    threat_mask = region_mask(threat_center, threat_width)

    results: dict[str, dict] = {}
    median_traces: dict[str, np.ndarray] = {}

    conditions = [
        ("Repo_Obs_ON_Move_ON",  True,  True),
        ("Repo_Obs_ON_Move_OFF", True,  False),
        ("Repo_Obs_OFF",         False, False),
    ]

    for name, obs_on, move_on in conditions:
        traces = []
        xs = []
        per_seed = {}

        for seed in seeds:
            rng = np.random.default_rng(seed)
            x = np.zeros(L, dtype=np.float64)

            x_start = start_x0
            x[x_start:x_start+N] = genome
            target = genome.copy()

            fidelity = np.zeros(steps, dtype=np.float64)
            x_pos = np.zeros(steps, dtype=np.int32)

            W_env = 0.0
            W_fb = 0.0
            W_obs = 0.0
            moves = 0

            for t in range(steps):
                # ---- warning field (vector over lattice)
                if warn_step <= t < pulse_start:
                    phase = 2.0 * np.pi * (t - warn_step) / 200.0
                    warn = (eta_warn * np.sin(phase)) * threat_mask
                    warn += rng.normal(0.0, eta_warn * 0.15, size=L) * threat_mask
                else:
                    warn = np.zeros(L, dtype=np.float64)

                # ---- pulse field (vector over lattice)
                if pulse_start <= t < (pulse_start + pulse_dur):
                    pulse = rng.normal(0.0, eta_pulse, size=L) * threat_mask
                    W_env += float(np.sum(pulse * pulse))
                else:
                    pulse = np.zeros(L, dtype=np.float64)

                # ---- movement decision (pre-pulse only)
                if move_on and obs_on and (warn_step <= t < pulse_start) and (moves < max_moves):
                    wwin = warn[x_start:x_start+N]
                    e = float(np.sum(wwin * wwin))
                    if e > warn_energy_thresh:
                        # move AWAY from threat center
                        direction = 1 if x_start >= threat_center else -1
                        new_start = int(np.clip(x_start + direction * step_size, 0, L - N))
                        if new_start != x_start:
                            seg = x[x_start:x_start+N].copy()
                            x[x_start:x_start+N] = 0.0
                            x[new_start:new_start+N] = seg
                            x_start = new_start
                            moves += 1

                # ---- dynamics update
                lap = laplacian(x)

                seg = x[x_start:x_start+N]
                err = target - seg

                if obs_on:
                    fb_u = np.clip(k_fb * err, -u_max, u_max)
                    ob_u = np.clip(k_obs * err, -u_max, u_max)
                else:
                    fb_u = np.zeros_like(err)
                    ob_u = np.zeros_like(err)

                seg = seg + dt * (k_diff * lap[x_start:x_start+N] + fb_u + ob_u) \
                        + warn[x_start:x_start+N] \
                        + pulse[x_start:x_start+N]

                x[x_start:x_start+N] = seg

                W_fb += float(np.sum(fb_u * fb_u))
                W_obs += float(np.sum(ob_u * ob_u))

                fidelity[t] = cosine_similarity(seg, target)
                x_pos[t] = x_start

            traces.append(fidelity)
            xs.append(x_pos)

            per_seed[str(seed)] = {
                "summary": {
                    "auc": float(np.mean(fidelity)),
                    "delta_x_pre_pulse": int(x_pos[pulse_start - 1] - start_x0),
                    "moves": int(moves),
                    "W_env_pulse": float(W_env),
                    "W_feedback": float(W_fb),
                    "W_observer": float(W_obs),
                    "W_total": float(W_env + W_fb + W_obs),
                }
            }

        traces = np.stack(traces, axis=0)
        xs = np.stack(xs, axis=0)

        median_traces[name] = np.median(traces, axis=0)
        median_x = np.median(xs, axis=0)

        aucs = [per_seed[str(s)]["summary"]["auc"] for s in seeds]
        dxs = [per_seed[str(s)]["summary"]["delta_x_pre_pulse"] for s in seeds]
        Ws = [per_seed[str(s)]["summary"]["W_total"] for s in seeds]

        results[name] = {
            "aggregate": {
                "auc_median": float(np.median(aucs)),
                "delta_x_median": float(np.median(dxs)),
                "W_total_median": float(np.median(Ws)),
            },
            "per_seed": per_seed,
            "median_trace": {
                "fidelity": median_traces[name][::10].tolist(),
                "x_start": median_x[::10].astype(int).tolist(),
                "dt_sampled": dt * 10,
            },
        }

    # ---- plots
    t = np.arange(steps) * dt
    pulse_t0 = pulse_start * dt
    pulse_t1 = (pulse_start + pulse_dur) * dt
    warn_t0 = warn_step * dt

    plt.figure(figsize=(12, 6))
    for name in median_traces:
        plt.plot(t, median_traces[name], label=name)
    plt.axvline(warn_t0, linestyle="--", linewidth=2)
    plt.axvspan(pulse_t0, pulse_t1, alpha=0.15)
    plt.axhline(0.90, linestyle="--", linewidth=2)
    plt.ylim(-0.05, 1.05)
    plt.title("P5v — Volition: fidelity (warning then pulse)")
    plt.xlabel("time")
    plt.ylabel("fidelity (cosine similarity)")
    plt.legend(loc="lower left")
    p_fid = OUT_DIR / "PAEV_P5v_Volition_Fidelity.png"
    plt.tight_layout()
    plt.savefig(p_fid, dpi=200)
    plt.close()

    plt.figure(figsize=(12, 4))
    for name in results:
        xs_plot = np.array(results[name]["median_trace"]["x_start"])
        tt = np.arange(xs_plot.size) * results[name]["median_trace"]["dt_sampled"]
        plt.plot(tt, xs_plot, label=name)
    plt.axvline(warn_t0, linestyle="--", linewidth=2)
    plt.axvline(pulse_t0, linestyle="--", linewidth=2)
    plt.title("P5v — Volition: genome window displacement (median)")
    plt.xlabel("time")
    plt.ylabel("window start index")
    plt.legend(loc="best")
    p_x = OUT_DIR / "PAEV_P5v_Volition_Displacement.png"
    plt.tight_layout()
    plt.savefig(p_x, dpi=200)
    plt.close()

    out = {
        "timestamp": utc_ts(),
        "run_id": run_id,
        "git_rev": git_rev(),
        "constants": const,
        "params": {
            "lattice_size": L,
            "genome_len": N,
            "dt": dt,
            "steps_total": steps,
            "seed_list": seeds,
            "warning": {
                "start_step": warn_step,
                "eta_warn": eta_warn,
                "threat_center": threat_center,
                "threat_width": threat_width,
            },
            "pulse": {
                "start_step": pulse_start,
                "duration_steps": pulse_dur,
                "eta_pulse": eta_pulse,
                "target": "threat_region",
            },
            "movement": {
                "enabled_in": "Repo_Obs_ON_Move_ON only",
                "warn_energy_thresh": warn_energy_thresh,
                "step_size": step_size,
                "max_moves": max_moves,
            },
            "repo_weights": {"path": g_path, "sha256": g_sha},
            "dynamics": {"k_diff": k_diff, "k_fb": k_fb, "k_obs": k_obs, "u_max": u_max},
        },
        "definitions": {
            "success": "delta_x_pre_pulse != 0 (displacement before pulse) with bounded work proxy",
            "W_p": "model-scoped work proxy; see P4s schema components",
        },
        "conditions": results,
        "files": {
            "fidelity_plot": str(p_fid.name),
            "displacement_plot": str(p_x.name),
        },
    }

    out_json = OUT_DIR / "P5v_volition_protocol.json"
    out_json.write_text(json.dumps(out, indent=2))
    print("=== P5v — Volition Protocol ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_fid}")
    print(f"✅ PNG  -> {p_x}")
    print(f"RUN_ID  -> {run_id}")


if __name__ == "__main__":
    main()
