import os, json, hashlib, subprocess
from pathlib import Path
from datetime import datetime, UTC

import numpy as np
import matplotlib.pyplot as plt

from backend.photon_algebra.utils.load_constants import load_constants


# ----------------------------
# utilities
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
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    na = float(np.linalg.norm(a) + 1e-12)
    nb = float(np.linalg.norm(b) + 1e-12)
    return float(np.dot(a, b) / (na * nb))

def spectral_entropy_real(x: np.ndarray) -> float:
    """
    Robust spectral entropy for real-valued vectors.
    (P6 earlier crash was dtype-related; force float64.)
    """
    x = np.asarray(x, dtype=np.float64)
    X = np.fft.rfft(x)
    P = (np.abs(X) ** 2).astype(np.float64)
    P /= (P.sum() + 1e-12)
    H = -np.sum(P * np.log(P + 1e-12))
    H /= np.log(P.size + 1e-12)
    return float(H)

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

def load_repo_bits(n: int) -> tuple[np.ndarray, str, str]:
    wfile = find_weights_file()
    raw = wfile.read_bytes()
    h = sha256_bytes(raw)
    b = np.frombuffer(raw, dtype=np.uint8)
    return b[:n].copy(), h, str(wfile)


# ----------------------------
# operator dictionary (hardcoded)
# ----------------------------
def op_matrix(sym: str) -> np.ndarray:
    # acts on [re, im]^T
    if sym == "A":
        # +pi/2 rotation
        return np.array([[0.0, -1.0],
                         [1.0,  0.0]], dtype=np.float64)
    if sym == "C":
        # amplitude gain
        return np.array([[1.5, 0.0],
                         [0.0, 1.5]], dtype=np.float64)
    if sym == "G":
        # identity (local damping handled separately by chi boost)
        return np.array([[1.0, 0.0],
                         [0.0, 1.0]], dtype=np.float64)
    if sym == "T":
        # termination: project imag -> 0
        return np.array([[1.0, 0.0],
                         [0.0, 0.0]], dtype=np.float64)
    raise ValueError(f"Unknown symbol: {sym}")

def apply_code(code: str, z: np.ndarray, t: int) -> np.ndarray:
    """
    z: shape (2,) = [re, im]
    """
    sym = code[t % len(code)]
    M = op_matrix(sym)
    return M @ z


# ----------------------------
# dynamics
# ----------------------------
def laplacian(x: np.ndarray) -> np.ndarray:
    return np.roll(x, -1) + np.roll(x, 1) - 2.0 * x

def gaussian_pulse(L: int, center: int, sigma: float, amp: float) -> np.ndarray:
    i = np.arange(L, dtype=np.float64)
    g = np.exp(-0.5 * ((i - center) / (sigma + 1e-12)) ** 2)
    return (amp * g).astype(np.float64)


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # lattice + windows
    L = 4096
    N = 512

    # baseline positions (distance sweep overrides)
    xA0 = 768
    xB0 = 2304

    # time
    dt = 0.01
    steps = 3000
    seeds = [42, 43, 44, 45, 46]

    # controller
    k_fb = 2.5
    k_obs = 1.0
    u_max = 0.02
    k_diff = 2.0

    # chi well (local damping) applied only to "G" sites via code; here we model as extra damping term
    chi_boost = 0.15

    # perturbation protocol (the “Bell test”)
    perturb_step = 1000
    perturb_amp = 0.5
    perturb_sigma = 32.0

    # experiment sweeps
    code_pairs = [
        ("ACG", "TTA"),   # baseline
        ("GGG", "TTT"),
        ("AAA", "CCC"),
        ("ACG", "GCA"),
        ("ACGT", "TGCA"),
    ]
    distance_sweep = [256, 512, 1024, 1536]  # separation (B_start - A_start)

    # weights-derived bits used only to seed initial carrier phases deterministically
    bits, w_sha, w_path = load_repo_bits(4096)

    run_id = f"P6_1{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P6_1"

    def build_target(code: str) -> np.ndarray:
        """
        Build a real-valued target pattern (length N) by evolving a complex carrier
        under operator code, then taking real component.
        """
        z = np.array([1.0, 0.0], dtype=np.float64)
        tgt = np.zeros(N, dtype=np.float64)
        for t in range(N):
            z = apply_code(code, z, t)
            tgt[t] = z[0]
        # normalize
        tgt /= (np.linalg.norm(tgt) + 1e-12)
        return tgt

    def run_one(codeA: str, codeB: str, controller_on: bool, xA: int, xB: int) -> dict:
        tgtA = build_target(codeA)
        tgtB = build_target(codeB)

        x = np.zeros(L, dtype=np.float64)
        x[xA:xA+N] = tgtA
        x[xB:xB+N] = tgtB

        simA = np.zeros(steps, dtype=np.float64)
        simB = np.zeros(steps, dtype=np.float64)
        cohA = np.zeros(steps, dtype=np.float64)
        cohB = np.zeros(steps, dtype=np.float64)
        EA = np.zeros(steps, dtype=np.float64)
        EB = np.zeros(steps, dtype=np.float64)

        W_fb = 0.0
        W_obs = 0.0
        W_drive = 0.0

        # perturbation applied to WINDOW A center
        pulse = gaussian_pulse(L, center=xA + N//2, sigma=perturb_sigma, amp=perturb_amp)

        for t in range(steps):
            lap = laplacian(x)

            # windows
            wA = x[xA:xA+N]
            wB = x[xB:xB+N]

            # controller
            if controller_on:
                eA = tgtA - wA
                eB = tgtB - wB
                uA_fb = np.clip(k_fb * eA, -u_max, u_max)
                uA_ob = np.clip(k_obs * eA, -u_max, u_max)
                uB_fb = np.clip(k_fb * eB, -u_max, u_max)
                uB_ob = np.clip(k_obs * eB, -u_max, u_max)
            else:
                uA_fb = np.zeros_like(wA)
                uA_ob = np.zeros_like(wA)
                uB_fb = np.zeros_like(wB)
                uB_ob = np.zeros_like(wB)

            # chi damping: emulate extra loss where code has 'G'
            # (simple proxy: multiply by (1 - chi_boost*dt) at G positions)
            gmaskA = np.array([1.0 if codeA[i % len(codeA)] == "G" else 0.0 for i in range(N)], dtype=np.float64)
            gmaskB = np.array([1.0 if codeB[i % len(codeB)] == "G" else 0.0 for i in range(N)], dtype=np.float64)

            wA = wA + dt * (k_diff * lap[xA:xA+N] + uA_fb + uA_ob) - dt * chi_boost * gmaskA * wA
            wB = wB + dt * (k_diff * lap[xB:xB+N] + uB_fb + uB_ob) - dt * chi_boost * gmaskB * wB

            # perturbation at t=perturb_step hits the lattice (couples through diffusion)
            if t == perturb_step:
                x = x + pulse
                W_drive += float(np.sum(pulse * pulse))

            x[xA:xA+N] = wA
            x[xB:xB+N] = wB

            W_fb += float(np.sum(uA_fb*uA_fb) + np.sum(uB_fb*uB_fb))
            W_obs += float(np.sum(uA_ob*uA_ob) + np.sum(uB_ob*uB_ob))

            simA[t] = cosine_similarity(wA, tgtA)
            simB[t] = cosine_similarity(wB, tgtB)

            # coherence proxy: |mean(window)| / mean(|window|)
            cohA[t] = float(np.abs(np.mean(wA)) / (np.mean(np.abs(wA)) + 1e-12))
            cohB[t] = float(np.abs(np.mean(wB)) / (np.mean(np.abs(wB)) + 1e-12))

            EA[t] = float(np.sum(wA*wA))
            EB[t] = float(np.sum(wB*wB))

        # perturbation response metric in window B (lag to max coherence change)
        dcohB = np.abs(cohB - cohB[perturb_step])
        lag = int(np.argmax(dcohB[perturb_step:]) + perturb_step) - perturb_step
        resp_mag = float(np.max(dcohB[perturb_step:]))

        out = {
            "summary": {
                "E_A0": float(EA[0]),
                "E_B0": float(EB[0]),
                "E_A_end": float(EA[-1]),
                "E_B_end": float(EB[-1]),
                "energy_transfer_index_dE": float((EA[-1]-EA[0]) - (EB[-1]-EB[0])),
                "auc_similarity_A": float(np.mean(simA)),
                "auc_similarity_B": float(np.mean(simB)),
                "coherence_drop": float(0.5*(cohA[0]+cohB[0]) - 0.5*(cohA[-1]+cohB[-1])),
                "auc_entropy": float(np.mean([spectral_entropy_real(x)])),  # coarse; global snapshot proxy
                "perturb_lag_B_steps": int(lag),
                "perturb_resp_mag_B": float(resp_mag),
                "W_feedback": float(W_fb),
                "W_observer": float(W_obs),
                "W_drive": float(W_drive),
                "W_total": float(W_fb + W_obs + W_drive),
            }
        }
        return out

    # aggregate results
    results = {}

    # two high-level experiment blocks:
    # (A) code-pair sweep at fixed distance
    # (B) distance sweep for baseline code pair
    experiments = []

    for codeA, codeB in code_pairs:
        experiments.append(("code_pair", {"codeA": codeA, "codeB": codeB, "xA": xA0, "xB": xB0}))

    for sep in distance_sweep:
        experiments.append(("distance", {"codeA": "ACG", "codeB": "TTA", "xA": xA0, "xB": xA0 + sep}))

    for kind, cfg in experiments:
        tag = f"{kind}__A_{cfg['codeA']}__B_{cfg['codeB']}__sep_{cfg['xB']-cfg['xA']}"
        for controller_on in [False, True]:
            cname = f"{tag}__Controller_{'ON' if controller_on else 'OFF'}"
            per_seed = {}
            for s in seeds:
                # seed enters only through deterministic numpy RNG if you later extend noise;
                # currently kept deterministic for clean coupling measurement.
                per_seed[str(s)] = run_one(cfg["codeA"], cfg["codeB"], controller_on, cfg["xA"], cfg["xB"])

            # medians
            keys = list(next(iter(per_seed.values()))["summary"].keys())
            agg = {}
            for k in keys:
                vals = [per_seed[str(s)]["summary"][k] for s in seeds]
                agg[f"{k}_median"] = float(np.median(vals))

            results[cname] = {"aggregate": agg, "per_seed": per_seed, "config": cfg}

    # minimal plots: show effect sizes for response lag + response magnitude
    # (pull from aggregates)
    labels = []
    lag_on = []
    lag_off = []
    mag_on = []
    mag_off = []
    for k,v in results.items():
        if "__Controller_ON" in k and k.startswith("code_pair__"):
            base = k.replace("__Controller_ON","")
            off = base + "__Controller_OFF"
            labels.append(base.replace("code_pair__",""))
            lag_on.append(results[k]["aggregate"]["perturb_lag_B_steps_median"])
            mag_on.append(results[k]["aggregate"]["perturb_resp_mag_B_median"])
            lag_off.append(results[off]["aggregate"]["perturb_lag_B_steps_median"])
            mag_off.append(results[off]["aggregate"]["perturb_resp_mag_B_median"])

    if labels:
        xidx = np.arange(len(labels))

        plt.figure(figsize=(12,4))
        plt.plot(xidx, lag_off, label="Controller OFF")
        plt.plot(xidx, lag_on, label="Controller ON")
        plt.xticks(xidx, labels, rotation=30, ha="right")
        plt.ylabel("Window B perturbation lag (steps)")
        plt.title("P6.1 Coupling: perturbation lag in B across code pairs")
        plt.tight_layout()
        p_lag = OUT_DIR / "PAEV_P6_1_Coupling_Lag.png"
        plt.savefig(p_lag, dpi=200)
        plt.close()

        plt.figure(figsize=(12,4))
        plt.plot(xidx, mag_off, label="Controller OFF")
        plt.plot(xidx, mag_on, label="Controller ON")
        plt.xticks(xidx, labels, rotation=30, ha="right")
        plt.ylabel("Window B perturbation response magnitude")
        plt.title("P6.1 Coupling: perturbation response magnitude in B across code pairs")
        plt.tight_layout()
        p_mag = OUT_DIR / "PAEV_P6_1_Coupling_Response.png"
        plt.savefig(p_mag, dpi=200)
        plt.close()
    else:
        p_lag = None
        p_mag = None

    out = {
        "timestamp": utc_ts(),
        "run_id": run_id,
        "git_rev": git_rev(),
        "constants": const,
        "params": {
            "lattice_size": L,
            "window_len": N,
            "dt": dt,
            "steps_total": steps,
            "seeds": seeds,
            "controller": {"k_fb": k_fb, "k_obs": k_obs, "u_max": u_max, "k_diff": k_diff},
            "operators": {"A": "rot(+pi/2)", "C": "gain(1.5x)", "G": "chi_well(damping)", "T": "project_imag->0"},
            "chi_boost": chi_boost,
            "perturbation": {"step": perturb_step, "amp": perturb_amp, "sigma": perturb_sigma, "target": "Window A center"},
            "code_pairs": code_pairs,
            "distance_sweep": distance_sweep,
            "repo_weights": {"path": w_path, "sha256": w_sha},
        },
        "definitions": {
            "goal": "Measure code-dependent coupling signatures via perturbation-response + sweeps.",
            "non_claims": [
                "No syntax/communication claim unless code dependence exceeds diffusion-only baselines.",
            ],
        },
        "results": results,
        "files": {
            "lag_plot": (str(p_lag.name) if p_lag else None),
            "response_plot": (str(p_mag.name) if p_mag else None),
        },
    }

    out_json = OUT_DIR / "P6_1_coupling_perturbation.json"
    out_json.write_text(json.dumps(out, indent=2))

    print("=== P6.1 — Coupling / Perturbation / Sweeps ===")
    print(f"✅ JSON -> {out_json}")
    if p_lag: print(f"✅ PNG  -> {OUT_DIR / p_lag.name}")
    if p_mag: print(f"✅ PNG  -> {OUT_DIR / p_mag.name}")
    print(f"RUN_ID  -> {run_id}")


if __name__ == "__main__":
    main()