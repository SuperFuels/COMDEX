# backend/photon_algebra/tests/paev_test_P10_2_capacity_scaling.py
from __future__ import annotations

import os
import json
import hashlib
import subprocess
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


def corr_safe(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = min(a.size, b.size)
    a = a[:n] - float(np.mean(a[:n]))
    b = b[:n] - float(np.mean(b[:n]))
    sa = float(np.std(a))
    sb = float(np.std(b))
    if sa < 1e-12 or sb < 1e-12:
        return 0.0
    return float(np.mean(a * b) / (sa * sb))


def _seed_from_bytes(b: bytes) -> int:
    h = hashlib.sha256(b).digest()
    return int.from_bytes(h[:8], "little", signed=False)


def find_weights_file() -> Path:
    env = os.environ.get("WEIGHTS_PATH", "").strip()
    if env:
        p = Path(env)
        if p.exists() and p.is_file():
            return p
        raise FileNotFoundError(f"WEIGHTS_PATH set but not found: {p}")

    patterns = ("*.safetensors", "*.pth", "*.pt", "*.bin", "*.ckpt", "*.npz", "*.onnx")
    roots = [Path("."), Path("backend"), Path("models"), Path("weights"), Path("checkpoints")]
    candidates: list[Path] = []
    for r in roots:
        if not r.exists():
            continue
        for pat in patterns:
            candidates += list(r.rglob(pat))
    candidates = [p for p in candidates if p.is_file() and p.stat().st_size > 1024 * 128]
    if not candidates:
        raise FileNotFoundError("No weight file found. Set WEIGHTS_PATH=...")
    return max(candidates, key=lambda p: p.stat().st_size)


def load_repo_bits(n: int) -> tuple[np.ndarray, str, str, bytes]:
    wfile = find_weights_file()
    raw = wfile.read_bytes()
    h = sha256_bytes(raw)
    b = np.frombuffer(raw, dtype=np.uint8)
    return b[:n].copy(), h, str(wfile), raw


# ----------------------------
# operator dictionary (hardcoded)
# ----------------------------
def op_matrix(sym: str) -> np.ndarray:
    if sym == "A":
        return np.array([[0.0, -1.0], [1.0, 0.0]], dtype=np.float64)
    if sym == "C":
        return np.array([[1.5, 0.0], [0.0, 1.5]], dtype=np.float64)
    if sym == "G":
        return np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float64)
    if sym == "T":
        return np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.float64)
    raise ValueError(f"Unknown symbol: {sym}")


def apply_code(code: str, z: np.ndarray, t: int) -> np.ndarray:
    sym = code[t % len(code)]
    return op_matrix(sym) @ z


def build_target(code: str, N: int) -> np.ndarray:
    z = np.array([1.0, 0.0], dtype=np.float64)
    tgt = np.zeros(N, dtype=np.float64)
    for t in range(N):
        z = apply_code(code, z, t)
        tgt[t] = z[0]
    tgt /= (np.linalg.norm(tgt) + 1e-12)
    return tgt


# ----------------------------
# dynamics
# ----------------------------
def laplacian(x: np.ndarray) -> np.ndarray:
    return np.roll(x, -1) + np.roll(x, 1) - 2.0 * x


# ----------------------------
# PRN messages (block-aligned), low pairwise corr
# ----------------------------
def prn_pm1(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    bits = rng.integers(0, 2, size=int(n), dtype=np.int64)
    return (2.0 * bits - 1.0).astype(np.float64)


def make_lowcorr_set_pm1(
    K: int,
    nblocks: int,
    *,
    base_seed: int,
    warmup_blocks: int,
    target_abs_corr: float,
    max_tries: int,
) -> tuple[list[np.ndarray], list[int], float]:
    """
    Deterministically build K PRN ±1 sequences with low pairwise corr over post-warmup blocks.
    Returns (msgs, seeds_chosen, worst_abs_pair_corr).
    """
    sl = slice(int(warmup_blocks), int(nblocks))
    MIX = 0x9E3779B97F4A7C15

    msgs: list[np.ndarray] = []
    seeds: list[int] = []
    worst = 0.0

    for k in range(int(K)):
        base_k = (int(base_seed) ^ int(0x1111_1111 * (k + 1))) & 0xFFFFFFFFFFFFFFFF

        if k == 0:
            m = prn_pm1(nblocks, int(base_k))
            msgs.append(m)
            seeds.append(int(base_k))
            continue

        best_m = None
        best_seed = int(base_k)
        best_worst = 1e9

        for i in range(int(max_tries)):
            s = (int(base_k) ^ int((i + 1) * MIX)) & 0xFFFFFFFFFFFFFFFF
            cand = prn_pm1(nblocks, int(s))

            # worst abs corr vs existing
            w = 0.0
            ok = True
            for prev in msgs:
                c = abs(corr_safe(prev[sl], cand[sl]))
                w = max(w, float(c))
                if c > float(target_abs_corr):
                    ok = False
            if ok:
                best_m = cand
                best_seed = int(s)
                best_worst = float(w)
                break
            if w < best_worst:
                best_m = cand
                best_seed = int(s)
                best_worst = float(w)

        assert best_m is not None
        msgs.append(best_m)
        seeds.append(best_seed)

    # compute true worst over the selected set
    for i in range(len(msgs)):
        for j in range(i + 1, len(msgs)):
            c = abs(corr_safe(msgs[i][sl], msgs[j][sl]))
            worst = max(worst, float(c))

    return msgs, seeds, float(worst)


# ----------------------------
# Walsh/Hadamard chips (K<=8 with current block config)
# ----------------------------
def hadamard(n: int) -> np.ndarray:
    if n & (n - 1) != 0:
        raise ValueError("Hadamard size must be a power of 2")
    H = np.array([[1.0]], dtype=np.float64)
    while H.shape[0] < n:
        H = np.block([[H, H], [H, -H]])
    return H


def make_walsh_chip(steps: int, chip_spread: int, chips_per_block: int, row: int) -> np.ndarray:
    H = hadamard(int(chips_per_block))
    r = int(row) % int(chips_per_block)
    base = H[r]
    one_block = np.repeat(base, int(chip_spread)).astype(np.float64)
    reps = int(np.ceil(int(steps) / one_block.size))
    return np.tile(one_block, reps)[: int(steps)]


def demod_blocks_baseband(time_series: np.ndarray, chip: np.ndarray, *, steps: int, despread_box: int) -> np.ndarray:
    y = np.asarray(time_series, dtype=np.float64)
    z = y[: int(steps)] * chip[: int(steps)]
    nb = int(steps) // int(despread_box)
    z = z[: nb * int(despread_box)].reshape(nb, int(despread_box))
    return np.mean(z, axis=1)


# ----------------------------
# KxK block-rate unmixing
# ----------------------------
def estimate_mix_A_K(msgs_sym: list[np.ndarray], R: np.ndarray, slb: slice) -> np.ndarray:
    """
    Model: R (K,nb) ≈ A (K,K) * M (K,nb).
    Estimate A by LS: for each i, solve M^T a_i = r_i.
    """
    M = np.stack([m[slb] for m in msgs_sym], axis=0)  # (K,nb2)
    X = M.T  # (nb2,K)
    K = int(M.shape[0])

    A = np.zeros((K, K), dtype=np.float64)
    for i in range(K):
        y = R[i, slb]  # (nb2,)
        ai, *_ = np.linalg.lstsq(X, y, rcond=None)  # (K,)
        A[i, :] = ai
    return A


def unmix_K(A: np.ndarray, R: np.ndarray) -> np.ndarray:
    """
    Recover M_hat = A^{-1} R. Uses pinv if ill-conditioned.
    """
    try:
        invA = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        invA = np.linalg.pinv(A)
    return invA @ R


# ----------------------------
# receiver geometry
# ----------------------------
def make_receiver_positions(xA: int, K: int, sep: int, L: int, N: int) -> list[int]:
    """
    Alternate right/left growing radius: +sep, -sep, +2sep, -2sep, ...
    Clipped to valid window start.
    """
    out: list[int] = []
    for i in range(int(K)):
        sign = 1 if (i % 2 == 0) else -1
        mult = (i // 2) + 1
        x = int(xA + sign * mult * int(sep))
        x = int(np.clip(x, 0, int(L) - int(N)))
        out.append(x)
    return out


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fast = os.environ.get("P10_2_FAST", "0").strip() not in ("0", "", "false", "False")
    jobs_env = int(os.environ.get("P10_2_JOBS", os.environ.get("P10_JOBS", "1")))  # recorded only

    # lattice / windows
    L = 4096
    N = 512
    xA = 2048 - N // 2

    # time
    dt = 0.01

    # DSSS params (fixed)
    chip_spread = 64
    despread_box = 512
    chips_per_block = despread_box // chip_spread  # 8 => max orth rows = 8

    # sweep
    if fast:
        steps_raw = 16384  # 32 blocks
        seeds = [42]
        separations = [1024]
        warmup_steps = 1024  # 2 blocks
        K_list = [3, 4, 6, 8]
    else:
        steps_raw = 65536  # 128 blocks
        seeds = [42, 43, 44]
        separations = [512, 1024, 1536]
        warmup_steps = 2048  # 4 blocks
        K_list = [3, 4, 5, 6, 7, 8]

    # align
    steps = (steps_raw // despread_box) * despread_box
    nblocks = steps // despread_box
    warmup_steps = (warmup_steps // despread_box) * despread_box
    warmup_blocks = max(1, warmup_steps // despread_box)
    warmup_blocks = int(min(warmup_blocks, max(1, nblocks // 8)))
    slb = slice(warmup_blocks, nblocks)

    # controller (linear)
    controller_on = True
    k_fb = 2.5
    k_obs = 1.0
    k_diff = 2.0
    chi_boost = 0.15

    # target (identical windows)
    code = "ACG"
    tgt = build_target(code, N)
    gmask = np.array([1.0 if code[i % len(code)] == "G" else 0.0 for i in range(N)], dtype=np.float64)

    # drive
    drive_amp = float(os.environ.get("P10_2_DRIVE_AMP", "0.010"))
    alpha = float(os.environ.get("P10_2_ALPHA", "0.75"))
    meas_noise_sigma = float(os.environ.get("P10_2_MEAS_NOISE", "2e-4"))

    # thresholds / scoring
    min_abs_main = float(os.environ.get("P10_2_MIN_MAIN", "0.25"))
    max_abs_xtalk = float(os.environ.get("P10_2_MAX_XTALK", "0.18" if fast else "0.15"))
    target_abs_corr = float(os.environ.get("P10_2_MSG_CORR_MAX", "0.05"))
    msg_corr_tries = int(os.environ.get("P10_2_MSG_CORR_TRIES", "256"))
    min_pass_K = int(os.environ.get("P10_2_MIN_PASS_K", "4"))

    # provenance seed
    _, w_sha, w_path, w_raw = load_repo_bits(4096)
    base_seed = _seed_from_bytes(w_raw) ^ 0xA5A5_1234

    run_id = f"P10_2{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P10_2_CAPACITY"

    def simulate_K(sep: int, K: int, mode: str, seed: int, m_time: list[np.ndarray], chips: list[np.ndarray]) -> dict:
        """
        mode:
          - "MOD_ON": multiplex sum_k m_k * chip_k
          - "MOD_OFF": drive=0
        Returns meanB: list length K, each array length steps.
        """
        rng = np.random.default_rng(int(seed))

        xBs = make_receiver_positions(xA, K, sep, L, N)
        x = np.zeros(L, dtype=np.float64)

        # initialize all windows to target
        x[xA : xA + N] = tgt
        for xb in xBs:
            x[xb : xb + N] = tgt
        x += rng.normal(0.0, 1e-6, size=L)

        meanB = [np.zeros(steps, dtype=np.float64) for _ in range(K)]
        W_fb = 0.0
        W_obs = 0.0
        W_drive = 0.0

        for t in range(steps):
            lap = laplacian(x)

            if mode == "MOD_ON":
                s = 0.0
                for k in range(K):
                    s += float(m_time[k][t] * chips[k][t])
                drive_scalar = float(drive_amp * alpha * s)
            else:
                drive_scalar = 0.0

            W_drive += float(L) * float(drive_scalar * drive_scalar)

            # update A window
            wA = x[xA : xA + N]
            if controller_on:
                eA = tgt - wA
                uA_fb = k_fb * eA
                uA_ob = k_obs * eA
            else:
                uA_fb = uA_ob = np.zeros_like(wA)

            wA = wA + dt * (k_diff * lap[xA : xA + N] + uA_fb + uA_ob) - dt * chi_boost * gmask * wA
            x[xA : xA + N] = wA
            W_fb += float(np.sum(uA_fb * uA_fb))
            W_obs += float(np.sum(uA_ob * uA_ob))

            # update receivers
            for i, xb in enumerate(xBs):
                wB = x[xb : xb + N]
                if controller_on:
                    eB = tgt - wB
                    uB_fb = k_fb * eB
                    uB_ob = k_obs * eB
                else:
                    uB_fb = uB_ob = np.zeros_like(wB)

                wB = wB + dt * (k_diff * lap[xb : xb + N] + uB_fb + uB_ob) - dt * chi_boost * gmask * wB
                x[xb : xb + N] = wB
                W_fb += float(np.sum(uB_fb * uB_fb))
                W_obs += float(np.sum(uB_ob * uB_ob))

                meanB[i][t] = float(np.mean(x[xb : xb + N])) + float(rng.normal(0.0, meas_noise_sigma))

            # global shared medium injection
            x += drive_scalar

        return {
            "meanB": meanB,
            "W_feedback": float(W_fb),
            "W_observer": float(W_obs),
            "W_drive": float(W_drive),
            "W_total": float(W_fb + W_obs + W_drive),
        }

    # ----------------------------
    # results container
    # ----------------------------
    results: dict = {
        "timestamp": utc_ts(),
        "run_id": run_id,
        "git_rev": git_rev(),
        "constants": const,
        "params": {
            "fast_mode": bool(fast),
            "jobs": int(jobs_env),
            "lattice_size": L,
            "window_len": N,
            "dt": dt,
            "steps_total": int(steps),
            "nblocks": int(nblocks),
            "warmup_blocks": int(warmup_blocks),
            "seeds": seeds,
            "separations": separations,
            "K_list": K_list,
            "code": code,
            "controller": {
                "controller_on": bool(controller_on),
                "linear_controller": True,
                "k_fb": float(k_fb),
                "k_obs": float(k_obs),
                "k_diff": float(k_diff),
                "chi_boost": float(chi_boost),
            },
            "messages": {
                "type": "PRN ±1 (pairwise low-corr search)",
                "target_abs_corr": float(target_abs_corr),
                "max_tries": int(msg_corr_tries),
            },
            "chip": {
                "type": "Walsh/Hadamard",
                "chip_spread": int(chip_spread),
                "despread_box": int(despread_box),
                "chips_per_block": int(chips_per_block),
                "rows_rule": "rows = [0..K-1] (Hadamard order)",
                "note": "chips_per_block=8 => K MUST be <= 8 for orth rows in this block config.",
            },
            "drive": {
                "drive_amp": float(drive_amp),
                "alpha": float(alpha),
                "meas_noise_sigma": float(meas_noise_sigma),
            },
            "scoring": {
                "min_abs_main": float(min_abs_main),
                "max_abs_xtalk": float(max_abs_xtalk),
                "min_pass_K_for_overall": int(min_pass_K),
            },
            "repo_weights": {"path": w_path, "sha256": w_sha},
        },
        "by_K": {},
        "summary": {},
        "checks": {},
        "definitions": {
            "goal": "P10.2 capacity scaling: increase K=3..8 users and measure main-corr distribution, max crosstalk vs K, and demix conditioning.",
            "notes": [
                "Receiver = RAW chip despread per user + block-rate linear unmix (KxK).",
                "Conditioning and pinv usage are logged as part of failure-mode reporting.",
            ],
        },
    }

    # ----------------------------
    # sweep
    # ----------------------------
    total_jobs = len(K_list) * len(separations) * len(seeds)
    job_idx = 0

    for K in K_list:
        if int(K) > int(chips_per_block):
            raise ValueError(f"K={K} exceeds chips_per_block={chips_per_block} (no orth Walsh rows)")

        results["by_K"][str(int(K))] = {"per_sep": {}, "aggregate": {}}

        # deterministic message set + chips for this K
        msgs_sym, msg_seeds, worst_pair_corr = make_lowcorr_set_pm1(
            int(K),
            int(nblocks),
            base_seed=int(base_seed),
            warmup_blocks=int(warmup_blocks),
            target_abs_corr=float(target_abs_corr),
            max_tries=int(msg_corr_tries),
        )
        msgs_time = [np.repeat(m, despread_box)[:steps].astype(np.float64) for m in msgs_sym]
        rows = list(range(int(K)))
        chips = [make_walsh_chip(steps, chip_spread, chips_per_block, row=r) for r in rows]

        # per-sep
        for sep in separations:
            per_seed = {}
            for s in seeds:
                job_idx += 1
                if fast:
                    print(f"[P10.2] {job_idx}/{total_jobs}: K={int(K)} sep={int(sep)} seed={int(s)}")

                sim_off = simulate_K(int(sep), int(K), "MOD_OFF", int(s), msgs_time, chips)
                sim_on = simulate_K(int(sep), int(K), "MOD_ON", int(s), msgs_time, chips)

                # demod each receiver against its own chip
                R = np.zeros((int(K), int(nblocks)), dtype=np.float64)
                for i in range(int(K)):
                    dB = sim_on["meanB"][i] - sim_off["meanB"][i]
                    R[i, :] = demod_blocks_baseband(dB, chips[i], steps=steps, despread_box=despread_box)

                # estimate A and unmix
                A = estimate_mix_A_K(msgs_sym, R, slb)
                condA = float(np.linalg.cond(A)) if np.isfinite(np.linalg.cond(A)) else float("inf")
                Mhat = unmix_K(A, R)

                # correlations: main and crosstalk per decoded stream
                main_rhos = []
                max_xtalks = []
                for i in range(int(K)):
                    rho_ii = corr_safe(Mhat[i, slb], msgs_sym[i][slb])
                    main_rhos.append(float(rho_ii))

                    xt = 0.0
                    for j in range(int(K)):
                        if j == i:
                            continue
                        xt = max(xt, abs(corr_safe(Mhat[i, slb], msgs_sym[j][slb])))
                    max_xtalks.append(float(xt))

                per_seed[str(int(s))] = {
                    "K": int(K),
                    "sep": int(sep),
                    "seed": int(s),
                    "message_seeds": [int(x) for x in msg_seeds],
                    "worst_abs_pair_corr_after_warmup": float(worst_pair_corr),
                    "rows": rows,
                    "condA": float(condA),
                    "main_rhos": [float(x) for x in main_rhos],
                    "max_xtalks": [float(x) for x in max_xtalks],
                    "main_rho_median": float(np.median(np.abs(np.asarray(main_rhos, dtype=np.float64)))),
                    "main_rho_min": float(np.min(np.abs(np.asarray(main_rhos, dtype=np.float64)))),
                    "max_xtalk_max": float(np.max(np.asarray(max_xtalks, dtype=np.float64))),
                    "W_total": float(sim_on["W_total"]),
                    "mix_A_T": A.T.tolist(),
                }

            # aggregate over seeds
            def med_seed(k: str) -> float:
                vals = [per_seed[str(int(ss))][k] for ss in seeds]
                return float(np.median(np.asarray(vals, dtype=np.float64)))

            results["by_K"][str(int(K))]["per_sep"][str(int(sep))] = {
                "per_seed": per_seed,
                "aggregate": {
                    "main_rho_median_over_users_median_over_seeds": med_seed("main_rho_median"),
                    "main_rho_min_over_users_median_over_seeds": med_seed("main_rho_min"),
                    "max_xtalk_max_median_over_seeds": med_seed("max_xtalk_max"),
                    "condA_median_over_seeds": med_seed("condA"),
                    "worst_abs_pair_corr_median_over_seeds": float(
                        np.median([per_seed[str(int(ss))]["worst_abs_pair_corr_after_warmup"] for ss in seeds])
                    ),
                },
            }

        # aggregate over seps
        def med_over_seps(key2: str) -> float:
            vals = [results["by_K"][str(int(K))]["per_sep"][str(int(sep))]["aggregate"][key2] for sep in separations]
            return float(np.median(np.asarray(vals, dtype=np.float64)))

        results["by_K"][str(int(K))]["aggregate"] = {
            "main_rho_median": med_over_seps("main_rho_median_over_users_median_over_seeds"),
            "main_rho_min": med_over_seps("main_rho_min_over_users_median_over_seeds"),
            "max_xtalk_max": med_over_seps("max_xtalk_max_median_over_seeds"),
            "condA_median": med_over_seps("condA_median_over_seeds"),
            "worst_abs_pair_corr_median": med_over_seps("worst_abs_pair_corr_median_over_seeds"),
        }

    # ----------------------------
    # pass per K + overall
    # ----------------------------
    pass_by_K: dict[str, bool] = {}
    highest_passing_K = 0
    for K in K_list:
        agg = results["by_K"][str(int(K))]["aggregate"]
        ok = True
        ok &= (float(agg["worst_abs_pair_corr_median"]) <= float(target_abs_corr))
        ok &= (float(agg["main_rho_median"]) >= float(min_abs_main))
        ok &= (float(agg["max_xtalk_max"]) <= float(max_abs_xtalk))
        pass_by_K[str(int(K))] = bool(ok)
        if ok:
            highest_passing_K = max(highest_passing_K, int(K))

    overall_ok = highest_passing_K >= int(min_pass_K)

    results["summary"] = {
        "pass_by_K": pass_by_K,
        "highest_passing_K": int(highest_passing_K),
        "min_pass_K_required": int(min_pass_K),
    }

    results["checks"] = {
        "overall_pass": bool(overall_ok),
        "criteria": {
            "min_abs_main": float(min_abs_main),
            "max_abs_xtalk": float(max_abs_xtalk),
            "target_abs_pair_corr": float(target_abs_corr),
            "min_pass_K_required": int(min_pass_K),
        },
        "observed": {
            "highest_passing_K": int(highest_passing_K),
            "pass_by_K": pass_by_K,
        },
    }

    # ----------------------------
    # plots
    # ----------------------------
    Ks = np.asarray([int(k) for k in K_list], dtype=np.int64)
    main_med = np.asarray([results["by_K"][str(int(k))]["aggregate"]["main_rho_median"] for k in Ks], dtype=np.float64)
    main_min = np.asarray([results["by_K"][str(int(k))]["aggregate"]["main_rho_min"] for k in Ks], dtype=np.float64)
    xt_max = np.asarray([results["by_K"][str(int(k))]["aggregate"]["max_xtalk_max"] for k in Ks], dtype=np.float64)
    condA = np.asarray([results["by_K"][str(int(k))]["aggregate"]["condA_median"] for k in Ks], dtype=np.float64)

    plt.figure(figsize=(10, 4))
    plt.plot(Ks, main_med, marker="o", label="median |rho_ii| (over users, med over seps)")
    plt.plot(Ks, main_min, marker="o", label="min |rho_ii| (over users, med over seps)")
    plt.axhline(min_abs_main, linestyle="--", linewidth=1.0, label="min_abs_main")
    plt.xlabel("K users")
    plt.ylabel("|correlation|")
    plt.title("P10.2 Capacity: main correlation vs K (post-demix)")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_main = OUT_DIR / "PAEV_P10_2_Capacity_MainRho_vs_K.png"
    plt.savefig(p_png_main, dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(Ks, xt_max, marker="o", label="max crosstalk (max over users, med over seps)")
    plt.axhline(max_abs_xtalk, linestyle="--", linewidth=1.0, label="max_abs_xtalk")
    plt.xlabel("K users")
    plt.ylabel("max |corr|")
    plt.title("P10.2 Capacity: max crosstalk vs K (post-demix)")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_xt = OUT_DIR / "PAEV_P10_2_Capacity_MaxCrosstalk_vs_K.png"
    plt.savefig(p_png_xt, dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(Ks, condA, marker="o", label="cond(A) median (over seps)")
    plt.yscale("log")
    plt.xlabel("K users")
    plt.ylabel("cond(A) (log scale)")
    plt.title("P10.2 Capacity: demix conditioning vs K")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_cond = OUT_DIR / "PAEV_P10_2_Capacity_CondA_vs_K.png"
    plt.savefig(p_png_cond, dpi=200)
    plt.close()

    out_json = OUT_DIR / "P10_2_capacity_scaling.json"
    out_json.write_text(json.dumps(results, indent=2) + "\n")

    print("=== P10.2 — Capacity Scaling (K users) ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_png_main}")
    print(f"✅ PNG  -> {p_png_xt}")
    print(f"✅ PNG  -> {p_png_cond}")
    print(f"RUN_ID  -> {run_id}")
    print(f"MODE    -> fast={bool(fast)} jobs={int(jobs_env)}")
    print(f"CHECKS  -> overall_pass={bool(overall_ok)} | highest_passing_K={int(highest_passing_K)}")


if __name__ == "__main__":
    main()