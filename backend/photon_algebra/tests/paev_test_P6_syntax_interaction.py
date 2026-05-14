# backend/photon_algebra/tests/paev_test_P6_syntax_interaction.py

import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, UTC

import numpy as np
import matplotlib.pyplot as plt

from backend.photon_algebra.utils.load_constants import load_constants


# -----------------------------
# util
# -----------------------------

def utc_ts() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")


def git_rev() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def cosine_similarity_complex(a: np.ndarray, b: np.ndarray) -> float:
    # complex cosine similarity via real/imag stacking
    ar = np.concatenate([a.real, a.imag]).astype(np.float64)
    br = np.concatenate([b.real, b.imag]).astype(np.float64)
    na = float(np.linalg.norm(ar) + 1e-12)
    nb = float(np.linalg.norm(br) + 1e-12)
    return float(np.dot(ar, br) / (na * nb))


def phase_coherence(z: np.ndarray) -> float:
    # |mean(exp(i*theta))| in [0,1]
    theta = np.angle(z)
    return float(np.abs(np.mean(np.exp(1j * theta))))


def spectral_entropy(x: np.ndarray) -> float:
    """
    Shannon entropy of the power spectrum of a real proxy of complex state.
    We use |x| (magnitude) to avoid phase-cancellation artifacts and to keep
    the metric real-valued and comparable across conditions.
    Returns normalized entropy in [0, 1].
    """
    xr = np.abs(x).astype(np.float64)  # real proxy
    X = np.fft.rfft(xr)
    p = (np.abs(X) ** 2).astype(np.float64)
    s = float(np.sum(p) + 1e-12)
    p = p / s
    H = -float(np.sum(p * np.log(p + 1e-12)))
    return float(H / (np.log(p.size + 1e-12)))


def laplacian_periodic(x: np.ndarray) -> np.ndarray:
    return np.roll(x, -1) + np.roll(x, 1) - 2.0 * x


# -----------------------------
# glyph operators (explicit)
# -----------------------------

# Represent phasor state z = re + i im as vector v=[re,im]
# and apply 2x2 real matrices.
OP_MATS = {
    # A: +pi/2 phase shift -> multiply by i
    "A": np.array([[0.0, -1.0],
                   [1.0,  0.0]], dtype=np.float64),

    # C: coherence boost (amp * 1.5)
    "C": np.array([[1.5, 0.0],
                   [0.0, 1.5]], dtype=np.float64),

    # T: termination / phase reset projection (imag -> 0)
    # (this is explicitly programmed; it enforces a boundary)
    "T": np.array([[1.0, 0.0],
                   [0.0, 0.0]], dtype=np.float64),

    # G: identity matrix on state; “mass well” is handled via chi_mask side-effect
    "G": np.eye(2, dtype=np.float64),
}


def apply_op(z: complex, sym: str) -> complex:
    M = OP_MATS[sym]
    v = np.array([z.real, z.imag], dtype=np.float64)
    out = M @ v
    return complex(float(out[0]), float(out[1]))


def build_target_from_code(code: str, N: int, chi0: float, chi_gain_G: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns:
      target (complex window length N)
      chi_mask (float window length N) : local damping/well coefficient
    """
    code = code.strip().upper()
    assert all(c in "ACGT" for c in code), f"code contains invalid symbols: {code}"

    target = np.zeros(N, dtype=np.complex128)
    chi_mask = np.zeros(N, dtype=np.float64)

    z = 1.0 + 0.0j  # carrier phasor (explicit initialization)
    for i in range(N):
        sym = code[i % len(code)]
        z = apply_op(z, sym)

        # optional extra explicit reset for T to represent boundary semantics
        if sym == "T":
            # normalize to positive real magnitude (hard boundary)
            z = complex(abs(z), 0.0)

        target[i] = z

        # “G creates a well”: increase local chi (damping / holding term)
        chi_mask[i] = chi0 * (chi_gain_G if sym == "G" else 1.0)

    # normalize target energy for stable comparisons
    target = target / (np.linalg.norm(target) + 1e-12)
    return target, chi_mask


# -----------------------------
# main P6 test
# -----------------------------

def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # lattice geometry
    L = 4096
    N = 1024

    # two windows (non-overlapping)
    start_A0 = 768
    start_B0 = 2304

    # time
    dt = 0.01
    steps = 4000
    seeds = [42, 43, 44, 45, 46]

    # dynamics
    k_diff = 1.6

    # chi baseline from constants if present
    chi0 = float(const.get("χ", const.get("chi", 1.0)))
    chi_scale = 0.15  # global scaling so chi doesn't overdamp
    chi_gain_G = 2.5  # how much "G" increases local well strength

    # optional stabilization controller (explicitly engineered)
    k_fb = 2.5
    k_obs = 1.0
    u_max = 0.015

    # codes (edit these)
    CODE_A = "ACG"
    CODE_B = "TTA"

    # optional broadcast drive (resonance probe)
    broadcast_on = False
    drive_amp = 0.02
    drive_w = 2.0 * np.pi / 1.0  # 1.0 time-unit period (dt-scaled)
    drive_phase = 0.0

    run_id = f"P6{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P6"
    meta = {
        "timestamp": utc_ts(),
        "run_id": run_id,
        "git_rev": git_rev(),
        "constants": const,
    }

    # build targets + chi masks (window-local)
    target_A, chiA = build_target_from_code(CODE_A, N, chi0, chi_gain_G)
    target_B, chiB = build_target_from_code(CODE_B, N, chi0, chi_gain_G)

    # embed chi masks into lattice field
    chi_field_base = np.zeros(L, dtype=np.float64)
    chi_field_base[start_A0:start_A0+N] = chiA
    chi_field_base[start_B0:start_B0+N] = chiB
    chi_field_base *= chi_scale

    conditions = [
        ("DualStrings_Controller_OFF", False),
        ("DualStrings_Controller_ON",  True),
    ]

    results = {}

    for cond_name, ctrl_on in conditions:
        per_seed = {}
        traces = []

        for seed in seeds:
            rng = np.random.default_rng(seed)

            # complex lattice state
            x = np.zeros(L, dtype=np.complex128)

            # place both targets
            x[start_A0:start_A0+N] = target_A
            x[start_B0:start_B0+N] = target_B

            # tiny background noise
            x += (rng.normal(0.0, 1e-4, size=L) + 1j * rng.normal(0.0, 1e-4, size=L)).astype(np.complex128)

            # metrics over time
            E_A = np.zeros(steps, dtype=np.float64)
            E_B = np.zeros(steps, dtype=np.float64)
            coh_A = np.zeros(steps, dtype=np.float64)
            coh_B = np.zeros(steps, dtype=np.float64)
            sim_A = np.zeros(steps, dtype=np.float64)
            sim_B = np.zeros(steps, dtype=np.float64)
            sim_AB = np.zeros(steps, dtype=np.float64)
            H_spec = np.zeros(steps, dtype=np.float64)

            W_fb = 0.0
            W_obs = 0.0
            W_drive = 0.0

            chi_field = chi_field_base.copy()

            for t in range(steps):
                lap = laplacian_periodic(x)

                # broadcast drive (global sinusoid) — resonance probe
                if broadcast_on:
                    drive = drive_amp * np.exp(1j * (drive_w * (t * dt) + drive_phase))
                    drive_vec = drive * np.ones(L, dtype=np.complex128)
                    W_drive += float(np.sum(np.abs(drive_vec) ** 2))
                else:
                    drive_vec = np.zeros(L, dtype=np.complex128)

                # controller acts only inside windows (explicitly engineered)
                u_fb_A = u_obs_A = np.zeros(N, dtype=np.complex128)
                u_fb_B = u_obs_B = np.zeros(N, dtype=np.complex128)

                if ctrl_on:
                    segA = x[start_A0:start_A0+N]
                    segB = x[start_B0:start_B0+N]

                    errA = target_A - segA
                    errB = target_B - segB

                    # clip by magnitude per-component (simple, explicit)
                    def clip_complex(u: np.ndarray, umax: float) -> np.ndarray:
                        mag = np.abs(u) + 1e-12
                        scale = np.minimum(1.0, umax / mag)
                        return u * scale

                    u_fb_A = clip_complex(k_fb * errA, u_max)
                    u_obs_A = clip_complex(k_obs * errA, u_max)
                    u_fb_B = clip_complex(k_fb * errB, u_max)
                    u_obs_B = clip_complex(k_obs * errB, u_max)

                    W_fb += float(np.sum(np.abs(u_fb_A) ** 2) + np.sum(np.abs(u_fb_B) ** 2))
                    W_obs += float(np.sum(np.abs(u_obs_A) ** 2) + np.sum(np.abs(u_obs_B) ** 2))

                # dynamics: diffusion + chi well (damping/holding) + drive
                x = x + dt * (k_diff * lap - chi_field * x) + drive_vec

                # inject controller contributions into windows only (explicit)
                if ctrl_on:
                    x[start_A0:start_A0+N] += dt * (u_fb_A + u_obs_A)
                    x[start_B0:start_B0+N] += dt * (u_fb_B + u_obs_B)

                # record metrics
                segA = x[start_A0:start_A0+N]
                segB = x[start_B0:start_B0+N]

                E_A[t] = float(np.sum(np.abs(segA) ** 2))
                E_B[t] = float(np.sum(np.abs(segB) ** 2))
                coh_A[t] = phase_coherence(segA)
                coh_B[t] = phase_coherence(segB)
                sim_A[t] = cosine_similarity_complex(segA, target_A)
                sim_B[t] = cosine_similarity_complex(segB, target_B)
                sim_AB[t] = cosine_similarity_complex(segA, segB)
                H_spec[t] = spectral_entropy(x)

            # summary measures (communication vs collision heuristics)
            # - energy transfer index: change in (E_A - E_B) over time
            dE = float((E_A[-1] - E_B[-1]) - (E_A[0] - E_B[0]))
            # - coherence drop: indicates decoherence / entropy growth
            coh_drop = float((coh_A[0] + coh_B[0]) * 0.5 - (coh_A[-1] + coh_B[-1]) * 0.5)
            # - similarity preservation
            auc_simA = float(np.mean(sim_A))
            auc_simB = float(np.mean(sim_B))
            auc_entropy = float(np.mean(H_spec))

            per_seed[str(seed)] = {
                "summary": {
                    "E_A0": float(E_A[0]),
                    "E_B0": float(E_B[0]),
                    "E_A_end": float(E_A[-1]),
                    "E_B_end": float(E_B[-1]),
                    "energy_transfer_index_dE": dE,
                    "coherence_A0": float(coh_A[0]),
                    "coherence_B0": float(coh_B[0]),
                    "coherence_A_end": float(coh_A[-1]),
                    "coherence_B_end": float(coh_B[-1]),
                    "coherence_drop": coh_drop,
                    "auc_similarity_A": auc_simA,
                    "auc_similarity_B": auc_simB,
                    "auc_entropy": auc_entropy,
                    "W_feedback": float(W_fb),
                    "W_observer": float(W_obs),
                    "W_drive": float(W_drive),
                    "W_total": float(W_fb + W_obs + W_drive),
                }
            }

            traces.append({
                "E_A": E_A,
                "E_B": E_B,
                "coh_A": coh_A,
                "coh_B": coh_B,
                "sim_A": sim_A,
                "sim_B": sim_B,
                "sim_AB": sim_AB,
                "H_spec": H_spec,
            })

        # aggregates
        def med(key: str) -> float:
            vals = [per_seed[str(s)]["summary"][key] for s in seeds]
            return float(np.median(vals))

        results[cond_name] = {
            "aggregate": {
                "energy_transfer_index_dE_median": med("energy_transfer_index_dE"),
                "coherence_drop_median": med("coherence_drop"),
                "auc_similarity_A_median": med("auc_similarity_A"),
                "auc_similarity_B_median": med("auc_similarity_B"),
                "auc_entropy_median": med("auc_entropy"),
                "W_total_median": med("W_total"),
            },
            "per_seed": per_seed,
            # median traces (downsampled)
            "median_trace": {
                "dt_sampled": dt * 10,
                "E_A": np.median(np.stack([tr["E_A"] for tr in traces], axis=0), axis=0)[::10].tolist(),
                "E_B": np.median(np.stack([tr["E_B"] for tr in traces], axis=0), axis=0)[::10].tolist(),
                "coh_A": np.median(np.stack([tr["coh_A"] for tr in traces], axis=0), axis=0)[::10].tolist(),
                "coh_B": np.median(np.stack([tr["coh_B"] for tr in traces], axis=0), axis=0)[::10].tolist(),
                "sim_A": np.median(np.stack([tr["sim_A"] for tr in traces], axis=0), axis=0)[::10].tolist(),
                "sim_B": np.median(np.stack([tr["sim_B"] for tr in traces], axis=0), axis=0)[::10].tolist(),
                "sim_AB": np.median(np.stack([tr["sim_AB"] for tr in traces], axis=0), axis=0)[::10].tolist(),
                "H_spec": np.median(np.stack([tr["H_spec"] for tr in traces], axis=0), axis=0)[::10].tolist(),
            },
        }

    # -----------------------------
    # plots (use median traces)
    # -----------------------------
    t = np.arange(steps // 10) * (dt * 10)

    # Energy plot
    plt.figure(figsize=(12, 5))
    for cond_name in results:
        EA = np.array(results[cond_name]["median_trace"]["E_A"])
        EB = np.array(results[cond_name]["median_trace"]["E_B"])
        plt.plot(t, EA, label=f"{cond_name}: E_A")
        plt.plot(t, EB, linestyle="--", label=f"{cond_name}: E_B")
    plt.title("P6 — Syntax Interaction: window energies (median)")
    plt.xlabel("time")
    plt.ylabel("energy (sum |z|^2)")
    plt.legend(loc="best", ncol=2)
    p_energy = OUT_DIR / "PAEV_P6_Syntax_Energy.png"
    plt.tight_layout()
    plt.savefig(p_energy, dpi=200)
    plt.close()

    # Coherence plot
    plt.figure(figsize=(12, 5))
    for cond_name in results:
        cA = np.array(results[cond_name]["median_trace"]["coh_A"])
        cB = np.array(results[cond_name]["median_trace"]["coh_B"])
        plt.plot(t, cA, label=f"{cond_name}: coh_A")
        plt.plot(t, cB, linestyle="--", label=f"{cond_name}: coh_B")
    plt.title("P6 — Syntax Interaction: phase coherence (median)")
    plt.xlabel("time")
    plt.ylabel("|mean(exp(i*theta))|")
    plt.ylim(-0.05, 1.05)
    plt.legend(loc="best", ncol=2)
    p_coh = OUT_DIR / "PAEV_P6_Syntax_Coherence.png"
    plt.tight_layout()
    plt.savefig(p_coh, dpi=200)
    plt.close()

    # Similarity/Entropy plot
    plt.figure(figsize=(12, 5))
    for cond_name in results:
        sA = np.array(results[cond_name]["median_trace"]["sim_A"])
        sB = np.array(results[cond_name]["median_trace"]["sim_B"])
        H  = np.array(results[cond_name]["median_trace"]["H_spec"])
        plt.plot(t, sA, label=f"{cond_name}: sim_A")
        plt.plot(t, sB, linestyle="--", label=f"{cond_name}: sim_B")
        plt.plot(t, H, linestyle=":", label=f"{cond_name}: spectral_entropy")
    plt.title("P6 — Syntax Interaction: similarity + spectral entropy (median)")
    plt.xlabel("time")
    plt.ylabel("metric value")
    plt.legend(loc="best", ncol=2)
    p_sim = OUT_DIR / "PAEV_P6_Syntax_Similarity_Entropy.png"
    plt.tight_layout()
    plt.savefig(p_sim, dpi=200)
    plt.close()

    out = {
        **meta,
        "params": {
            "lattice_size": L,
            "window_len": N,
            "dt": dt,
            "steps_total": steps,
            "seed_list": seeds,
            "starts": {"A": start_A0, "B": start_B0},
            "codes": {"A": CODE_A, "B": CODE_B},
            "operators": {
                "A": "phase shift +pi/2 (matrix [[0,-1],[1,0]])",
                "C": "amplitude x1.5 (matrix 1.5*I)",
                "G": "identity on phasor + increases local chi well",
                "T": "project imag->0 + magnitude reset (boundary)",
            },
            "dynamics": {
                "k_diff": k_diff,
                "chi0": chi0,
                "chi_scale": chi_scale,
                "chi_gain_G": chi_gain_G,
            },
            "controller": {
                "enabled_in": "DualStrings_Controller_ON only",
                "k_fb": k_fb,
                "k_obs": k_obs,
                "u_max": u_max,
            },
            "broadcast": {
                "enabled": broadcast_on,
                "drive_amp": drive_amp,
                "drive_w": drive_w,
                "drive_phase": drive_phase,
            },
        },
        "definitions": {
            "energy_transfer_index_dE": "Delta of (E_A - E_B) from start to end; nonzero suggests asymmetric transfer",
            "coherence": "|mean(exp(i*theta))| inside window",
            "spectral_entropy": "Shannon entropy of the power spectrum of |x| (magnitude), normalized",
            "scope_note": "This test measures engineered operator interactions in a complex lattice; it does not claim emergence/agency.",
        },
        "conditions": results,
        "files": {
            "energy_plot": str(p_energy.name),
            "coherence_plot": str(p_coh.name),
            "similarity_entropy_plot": str(p_sim.name),
        },
    }

    out_json = OUT_DIR / "P6_syntax_interaction.json"
    out_json.write_text(json.dumps(out, indent=2))

    print("=== P6 — Syntax Interaction / Glyph Operators ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_energy}")
    print(f"✅ PNG  -> {p_coh}")
    print(f"✅ PNG  -> {p_sim}")
    print(f"RUN_ID  -> {run_id}")


if __name__ == "__main__":
    main()