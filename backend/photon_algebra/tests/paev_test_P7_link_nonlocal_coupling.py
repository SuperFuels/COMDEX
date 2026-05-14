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
    if sym == "A":
        return np.array([[0.0, -1.0],
                         [1.0,  0.0]], dtype=np.float64)
    if sym == "C":
        return np.array([[1.5, 0.0],
                         [0.0, 1.5]], dtype=np.float64)
    if sym == "G":
        return np.array([[1.0, 0.0],
                         [0.0, 1.0]], dtype=np.float64)
    if sym == "T":
        return np.array([[1.0, 0.0],
                         [0.0, 0.0]], dtype=np.float64)
    raise ValueError(f"Unknown symbol: {sym}")

def apply_code(code: str, z: np.ndarray, t: int) -> np.ndarray:
    sym = code[t % len(code)]
    return op_matrix(sym) @ z


# ----------------------------
# dynamics
# ----------------------------
def laplacian(x: np.ndarray) -> np.ndarray:
    return np.roll(x, -1) + np.roll(x, 1) - 2.0 * x

def build_target(code: str, N: int) -> np.ndarray:
    z = np.array([1.0, 0.0], dtype=np.float64)
    tgt = np.zeros(N, dtype=np.float64)
    for t in range(N):
        z = apply_code(code, z, t)
        tgt[t] = z[0]
    tgt /= (np.linalg.norm(tgt) + 1e-12)
    return tgt

def coherence_proxy(w: np.ndarray) -> float:
    w = np.asarray(w, dtype=np.float64)
    return float(np.abs(np.mean(w)) / (np.mean(np.abs(w)) + 1e-12))

def gaussian_1d(idx: np.ndarray, center: float, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((idx - center) / (sigma + 1e-12)) ** 2)


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # lattice + windows
    L = 4096
    N = 512
    xA = 768
    sep = 1536
    xB = xA + sep

    # time
    dt = 0.01
    steps = 3000
    seeds = [42, 43, 44, 45, 46]

    # controller
    k_fb = 2.5
    k_obs = 1.0
    u_max = 0.02
    k_diff = 2.0

    # chi well (extra damping at G sites)
    chi_boost = 0.15

    # perturbation protocol
    perturb_step = 1000
    perturb_amp = 0.5
    perturb_sigma = 32.0

    # lag detectors (null if no detection)
    max_lag_steps = 1000
    thr_meanB = 1e-5
    thr_energyB = 1e-6

    # engineered nonlocal link strength sweep
    link_strengths = [0.0, 1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2]

    # link geometry: banded center-to-center edges
    center_A = xA + N // 2
    center_B = xB + N // 2
    band = 4
    link_offsets = list(range(-band, band + 1))  # 9 pairs when band=4

    # codes (baseline)
    codeA, codeB = "ACG", "TTA"

    _, w_sha, w_path = load_repo_bits(4096)
    run_id = f"P7B{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P7_LINK"

    def run_one(k_link: float, controller_on: bool, seed: int) -> dict:
        tgtA = build_target(codeA, N)
        tgtB = build_target(codeB, N)

        x = np.zeros(L, dtype=np.float64)
        x[xA:xA+N] = tgtA
        x[xB:xB+N] = tgtB

        simA = np.zeros(steps, dtype=np.float64)
        simB = np.zeros(steps, dtype=np.float64)

        meanB = np.zeros(steps, dtype=np.float64)
        energyB = np.zeros(steps, dtype=np.float64)
        cohB = np.zeros(steps, dtype=np.float64)

        W_fb = 0.0
        W_obs = 0.0
        W_drive = 0.0

        gmaskA = np.array([1.0 if codeA[i % len(codeA)] == "G" else 0.0 for i in range(N)], dtype=np.float64)
        gmaskB = np.array([1.0 if codeB[i % len(codeB)] == "G" else 0.0 for i in range(N)], dtype=np.float64)

        # perturbation pulse restricted to Window A (to avoid overwrite issues)
        idxA = np.arange(N, dtype=np.float64)
        pulseA = perturb_amp * gaussian_1d(idxA, center=float(N // 2), sigma=perturb_sigma)

        for t in range(steps):
            lap = laplacian(x)

            wA = x[xA:xA+N]
            wB = x[xB:xB+N]

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

            # update
            wA = wA + dt * (k_diff * lap[xA:xA+N] + uA_fb + uA_ob) - dt * chi_boost * gmaskA * wA
            wB = wB + dt * (k_diff * lap[xB:xB+N] + uB_fb + uB_ob) - dt * chi_boost * gmaskB * wB

            # perturb injection into wA (not x) so it survives writeback
            if t == perturb_step:
                wA = wA + pulseA
                W_drive += float(np.sum(pulseA * pulseA))

            x[xA:xA+N] = wA
            x[xB:xB+N] = wB

            # engineered nonlocal link (banded symmetric exchange; “graph edges”)
            if k_link > 0.0:
                for off in link_offsets:
                    ia = int(center_A + off)
                    ib = int(center_B + off)
                    # dt-scaled exchange (as recorded in JSON)
                    delta = dt * k_link * (x[ib] - x[ia])
                    x[ia] += delta
                    x[ib] -= delta

            W_fb += float(np.sum(uA_fb*uA_fb) + np.sum(uB_fb*uB_fb))
            W_obs += float(np.sum(uA_ob*uA_ob) + np.sum(uB_ob*uB_ob))

            simA[t] = cosine_similarity(x[xA:xA+N], tgtA)
            simB[t] = cosine_similarity(x[xB:xB+N], tgtB)

            wB2 = x[xB:xB+N]
            meanB[t] = float(np.mean(wB2))
            energyB[t] = float(np.sum(wB2 * wB2))
            cohB[t] = float(coherence_proxy(wB2))

        # response metrics in B after perturbation
        base_mean = float(meanB[perturb_step])
        base_energy = float(energyB[perturb_step])
        base_coh = float(cohB[perturb_step])

        d_mean = np.abs(meanB - base_mean)
        d_energy = np.abs(energyB - base_energy)
        d_coh = np.abs(cohB - base_coh)

        def first_lag(d: np.ndarray, thr: float) -> int | None:
            for tau in range(1, max_lag_steps + 1):
                t_idx = perturb_step + tau
                if t_idx >= steps:
                    break
                if float(d[t_idx]) > thr:
                    return int(tau)
            return None

        lag_mean = first_lag(d_mean, thr_meanB)
        lag_energy = first_lag(d_energy, thr_energyB)

        out = {
            "summary": {
                "k_link": float(k_link),
                "controller_on": bool(controller_on),
                "auc_similarity_A": float(np.mean(simA)),
                "auc_similarity_B": float(np.mean(simB)),
                "entropy_final": spectral_entropy_real(x),

                "perturb_resp_mag_meanB": float(np.max(d_mean[perturb_step:])),
                "perturb_resp_auc_meanB": float(np.mean(d_mean[perturb_step:])),
                "perturb_lag_meanB_steps": lag_mean,

                "perturb_resp_mag_energyB": float(np.max(d_energy[perturb_step:])),
                "perturb_resp_auc_energyB": float(np.mean(d_energy[perturb_step:])),
                "perturb_lag_energyB_steps": lag_energy,

                "perturb_resp_mag_cohB": float(np.max(d_coh[perturb_step:])),  # sanity (often ~numerical floor)

                "W_feedback": float(W_fb),
                "W_observer": float(W_obs),
                "W_drive": float(W_drive),
                "W_total": float(W_fb + W_obs + W_drive),
            }
        }
        return out

    results = {}
    controller_on = True
    for k_link in link_strengths:
        cname = f"LINK__sep_{sep}__k_{k_link:.0e}__Controller_{'ON' if controller_on else 'OFF'}"
        per_seed = {}
        for s in seeds:
            per_seed[str(s)] = run_one(k_link, controller_on, s)

        keys = list(next(iter(per_seed.values()))["summary"].keys())
        agg = {}
        for k in keys:
            vals = [per_seed[str(s)]["summary"][k] for s in seeds]
            if k in ("perturb_lag_meanB_steps", "perturb_lag_energyB_steps"):
                defined = [v for v in vals if v is not None]
                agg[f"{k}_median"] = (float(np.median(defined)) if defined else None)
            else:
                agg[f"{k}_median"] = float(np.median(vals))

        results[cname] = {"aggregate": agg, "per_seed": per_seed}

    # plots
    ks = []
    mag_mean = []
    mag_energy = []
    lag_mean = []
    lag_energy = []

    for k_link in link_strengths:
        cname = f"LINK__sep_{sep}__k_{k_link:.0e}__Controller_ON"
        ks.append(k_link)
        mag_mean.append(results[cname]["aggregate"]["perturb_resp_mag_meanB_median"])
        mag_energy.append(results[cname]["aggregate"]["perturb_resp_mag_energyB_median"])
        lag_mean.append(results[cname]["aggregate"]["perturb_lag_meanB_steps_median"])
        lag_energy.append(results[cname]["aggregate"]["perturb_lag_energyB_steps_median"])

    plt.figure(figsize=(8, 4))
    plt.plot(ks, mag_mean, marker="o", label="mean(B)")
    plt.plot(ks, mag_energy, marker="x", label="energy(B)")
    plt.xscale("symlog", linthresh=1e-5)
    plt.xlabel("k_link (nonlocal coupling strength)")
    plt.ylabel("median perturb response magnitude")
    plt.title("P7B Link: B response magnitude vs engineered nonlocal coupling")
    plt.legend(loc="best")
    plt.tight_layout()
    p_mag = OUT_DIR / "PAEV_P7B_Link_ResponseMag_vs_k.png"
    plt.savefig(p_mag, dpi=200)
    plt.close()

    plt.figure(figsize=(8, 4))
    lags_mean_num = [np.nan if v is None else v for v in lag_mean]
    lags_energy_num = [np.nan if v is None else v for v in lag_energy]
    plt.plot(ks, lags_mean_num, marker="o", label=f"lag mean(B) thr={thr_meanB:g}")
    plt.plot(ks, lags_energy_num, marker="x", label=f"lag energy(B) thr={thr_energyB:g}")
    plt.xscale("symlog", linthresh=1e-5)
    plt.xlabel("k_link (nonlocal coupling strength)")
    plt.ylabel("median lag (steps)")
    plt.title("P7B Link: B detection lag vs engineered nonlocal coupling")
    plt.legend(loc="best")
    plt.tight_layout()
    p_lag = OUT_DIR / "PAEV_P7B_Link_Lag_vs_k.png"
    plt.savefig(p_lag, dpi=200)
    plt.close()

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
            "codes": {"A": codeA, "B": codeB},
            "controller": {"k_fb": k_fb, "k_obs": k_obs, "u_max": u_max, "k_diff": k_diff},
            "operators": {"A": "rot(+pi/2)", "C": "gain(1.5x)", "G": "chi_well(damping)", "T": "project_imag->0"},
            "chi_boost": chi_boost,
            "geometry": {"xA": xA, "xB": xB, "sep": sep},
            "perturbation": {
                "step": perturb_step,
                "amp": perturb_amp,
                "sigma": perturb_sigma,
                "target": "Window A center (injected into wA to avoid overwrite)",
            },
            "lag_detector": {
                "max_lag_steps": max_lag_steps,
                "threshold_meanB": thr_meanB,
                "threshold_energyB": thr_energyB,
                "note": "No detection => lag is null (not saturated).",
            },
            "link": {
                "type": "engineered nonlocal adjacency (graph edge)",
                "k_link_sweep": link_strengths,
                "endpoints": {
                    "center_A": int(center_A),
                    "center_B": int(center_B),
                    "band": int(band),
                    "pairs": int(len(link_offsets)),
                },
                "update": "x[ia]+=dt*k_link*(x[ib]-x[ia]); x[ib]-=dt*k_link*(x[ib]-x[ia])",
                "note": "Explicit nonlocal coupling; not a physics claim.",
            },
            "repo_weights": {"path": w_path, "sha256": w_sha},
        },
        "definitions": {
            "goal": "P7B Link: quantify B response vs explicit nonlocal adjacency under A perturbation.",
            "non_claims": [
                "Nonlocal link is engineered; do not interpret as quantum entanglement or physical wormholes.",
            ],
        },
        "results": results,
        "files": {
            "response_plot": str(p_mag.name),
            "lag_plot": str(p_lag.name),
        },
    }

    out_json = OUT_DIR / "P7B_link_nonlocal_coupling.json"
    out_json.write_text(json.dumps(out, indent=2))

    print("=== P7B — Link / Nonlocal Coupling (PERTURB FIX + BETTER READOUT) ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {OUT_DIR / p_mag.name}")
    print(f"✅ PNG  -> {OUT_DIR / p_lag.name}")
    print(f"RUN_ID  -> {run_id}")


if __name__ == "__main__":
    main()