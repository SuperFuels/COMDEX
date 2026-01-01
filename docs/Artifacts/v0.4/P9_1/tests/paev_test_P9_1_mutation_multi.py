# backend/photon_algebra/tests/paev_test_P9_1_mutation_multi.py
from __future__ import annotations

import os
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, UTC
from concurrent.futures import ProcessPoolExecutor, as_completed

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
# deterministic PRN message (block-aligned)
# ----------------------------
def prn_pm1(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    bits = rng.integers(0, 2, size=int(n), dtype=np.int64)
    return (2.0 * bits - 1.0).astype(np.float64)


def make_lowcorr_pair_pm1(
    nblocks: int,
    *,
    seed1: int,
    seed2: int,
    warmup_blocks: int,
    target_abs_corr: float,
    max_tries: int = 256,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Deterministically choose msg2 so that corr(msg1, msg2) over post-warmup blocks
    is <= target_abs_corr (or as small as possible if not achievable).
    """
    msg1 = prn_pm1(nblocks, seed1)

    sl = slice(int(warmup_blocks), int(nblocks))
    best = None
    best_abs = 1e9
    best_corr = 0.0

    MIX = 0x9E3779B97F4A7C15  # deterministic “attempt” mixing constant

    for i in range(int(max_tries)):
        s2 = (int(seed2) ^ int((i + 1) * MIX)) & 0xFFFFFFFFFFFFFFFF
        cand2 = prn_pm1(nblocks, int(s2))
        c = corr_safe(msg1[sl], cand2[sl])
        ac = abs(float(c))
        if ac < best_abs:
            best_abs = ac
            best = cand2
            best_corr = float(c)
        if ac <= float(target_abs_corr):
            return msg1, cand2, float(c)

    # If not found, return best candidate (still deterministic)
    assert best is not None
    return msg1, best, best_corr


# ----------------------------
# Walsh/Hadamard chips
# ----------------------------
def hadamard(n: int) -> np.ndarray:
    if n & (n - 1) != 0:
        raise ValueError("Hadamard size must be a power of 2")
    H = np.array([[1.0]], dtype=np.float64)
    while H.shape[0] < n:
        H = np.block([[H, H], [H, -H]])
    return H


def make_walsh_chip(steps: int, chip_spread: int, chips_per_block: int, row: int) -> np.ndarray:
    H = hadamard(chips_per_block)
    r = int(row) % chips_per_block
    base = H[r]
    one_block = np.repeat(base, chip_spread).astype(np.float64)
    reps = int(np.ceil(steps / one_block.size))
    return np.tile(one_block, reps)[:steps]


def chip_block_inner(
    ch1: np.ndarray,
    ch2: np.ndarray,
    *,
    steps: int,
    despread_box: int,
    chips_per_block: int,
    chip_spread: int,
) -> np.ndarray:
    nb = steps // despread_box
    a = ch1[: nb * despread_box].reshape(nb, despread_box)
    b = ch2[: nb * despread_box].reshape(nb, despread_box)
    a_sym = a.reshape(nb, chips_per_block, chip_spread).mean(axis=2)
    b_sym = b.reshape(nb, chips_per_block, chip_spread).mean(axis=2)
    inn = np.sum(a_sym * b_sym, axis=1) / float(chips_per_block)
    return inn


def corrupt_receiver_chip_per_block(
    chip: np.ndarray,
    *,
    steps: int,
    despread_box: int,
    chips_per_block: int,
    chip_spread: int,
    k_flip: int,
    seed: int,
) -> np.ndarray:
    """
    Flip sign on k chip-symbol segments PER BLOCK (receiver-side only).
    """
    k = int(k_flip)
    if k <= 0:
        return chip.copy()
    if k >= chips_per_block:
        return (-chip).copy()

    rng = np.random.default_rng(int(seed))
    out = chip.copy()
    nb = steps // despread_box

    for b in range(nb):
        start = b * despread_box
        idx = rng.choice(chips_per_block, size=k, replace=False)
        for j in idx:
            s0 = start + j * chip_spread
            s1 = s0 + chip_spread
            out[s0:s1] *= -1.0
    return out


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


def demod_blocks_baseband(time_series: np.ndarray, chip: np.ndarray, *, steps: int, despread_box: int) -> np.ndarray:
    y = np.asarray(time_series, dtype=np.float64)
    z = y[:steps] * chip[:steps]
    nb = steps // despread_box
    z = z[: nb * despread_box].reshape(nb, despread_box)
    return np.mean(z, axis=1)


# ----------------------------
# worker (picklable) for parallel sims
# ----------------------------
def _simulate_pair_worker(payload: dict) -> tuple[tuple[int, int], dict]:
    sep = int(payload["sep"])
    seed = int(payload["seed"])
    params = payload["params"]

    # --- required sim params ---
    L = int(params["L"])
    N = int(params["N"])
    xA = int(params["xA"])
    dt = float(params["dt"])
    steps = int(params["steps"])
    code = str(params["code"])

    controller_on = bool(params["controller_on"])
    linear_controller = bool(params["linear_controller"])
    k_fb = float(params["k_fb"])
    k_obs = float(params["k_obs"])
    u_max = float(params["u_max"])
    k_diff = float(params["k_diff"])
    chi_boost = float(params["chi_boost"])

    drive_amp = float(params["drive_amp"])
    alpha = float(params["alpha"])
    meas_noise_sigma = float(params["meas_noise_sigma"])

    m1 = np.asarray(params["m1"], dtype=np.float64)
    m2 = np.asarray(params["m2"], dtype=np.float64)
    chip1 = np.asarray(params["chip1"], dtype=np.float64)
    chip2 = np.asarray(params["chip2"], dtype=np.float64)

    # --- optional params (safe defaults; avoids KeyError if missing) ---
    # (worker doesn't strictly need these, but keeping them safe makes future edits painless)
    _despread_box = int(params.get("despread_box", 512))
    _chip_spread = int(params.get("chip_spread", 64))
    _chips_per_block = int(params.get("chips_per_block", 8))

    xB1 = int(np.clip(xA + sep, 0, L - N))
    xB2 = int(np.clip(xA - sep, 0, L - N))

    tgt = build_target(code, N)
    gmask = np.array([1.0 if code[i % len(code)] == "G" else 0.0 for i in range(N)], dtype=np.float64)

    def sim(tx_on: bool, rng_local: np.random.Generator) -> dict:
        x = np.zeros(L, dtype=np.float64)
        x[xA : xA + N] = tgt
        x[xB1 : xB1 + N] = tgt
        x[xB2 : xB2 + N] = tgt
        x += rng_local.normal(0.0, 1e-6, size=L)

        meanB1 = np.zeros(steps, dtype=np.float64)
        meanB2 = np.zeros(steps, dtype=np.float64)

        W_fb = 0.0
        W_obs = 0.0
        W_drive = 0.0

        for t in range(steps):
            lap = laplacian(x)

            wA = x[xA : xA + N]
            wB1 = x[xB1 : xB1 + N]
            wB2 = x[xB2 : xB2 + N]

            drive_scalar = 0.0
            if tx_on:
                drive_scalar = drive_amp * (alpha * (m1[t] * chip1[t] + m2[t] * chip2[t]))

            W_drive += float(L) * float(drive_scalar * drive_scalar)

            if controller_on:
                eA = tgt - wA
                eB1 = tgt - wB1
                eB2 = tgt - wB2

                if linear_controller:
                    uA_fb = k_fb * eA
                    uA_ob = k_obs * eA
                    uB1_fb = k_fb * eB1
                    uB1_ob = k_obs * eB1
                    uB2_fb = k_fb * eB2
                    uB2_ob = k_obs * eB2
                else:
                    uA_fb = np.clip(k_fb * eA, -u_max, u_max)
                    uA_ob = np.clip(k_obs * eA, -u_max, u_max)
                    uB1_fb = np.clip(k_fb * eB1, -u_max, u_max)
                    uB1_ob = np.clip(k_obs * eB1, -u_max, u_max)
                    uB2_fb = np.clip(k_fb * eB2, -u_max, u_max)
                    uB2_ob = np.clip(k_obs * eB2, -u_max, u_max)
            else:
                uA_fb = uA_ob = np.zeros_like(wA)
                uB1_fb = uB1_ob = np.zeros_like(wB1)
                uB2_fb = uB2_ob = np.zeros_like(wB2)

            wA = wA + dt * (k_diff * lap[xA : xA + N] + uA_fb + uA_ob) - dt * chi_boost * gmask * wA
            wB1 = wB1 + dt * (k_diff * lap[xB1 : xB1 + N] + uB1_fb + uB1_ob) - dt * chi_boost * gmask * wB1
            wB2 = wB2 + dt * (k_diff * lap[xB2 : xB2 + N] + uB2_fb + uB2_ob) - dt * chi_boost * gmask * wB2

            x[xA : xA + N] = wA
            x[xB1 : xB1 + N] = wB1
            x[xB2 : xB2 + N] = wB2

            x += drive_scalar

            W_fb += float(np.sum(uA_fb * uA_fb) + np.sum(uB1_fb * uB1_fb) + np.sum(uB2_fb * uB2_fb))
            W_obs += float(np.sum(uA_ob * uA_ob) + np.sum(uB1_ob * uB1_ob) + np.sum(uB2_ob * uB2_ob))

            meanB1[t] = float(np.mean(x[xB1 : xB1 + N])) + float(rng_local.normal(0.0, meas_noise_sigma))
            meanB2[t] = float(np.mean(x[xB2 : xB2 + N])) + float(rng_local.normal(0.0, meas_noise_sigma))

        return {"meanB1": meanB1, "meanB2": meanB2, "W_total": float(W_fb + W_obs + W_drive)}

    # OFF/ON use independent but deterministic RNG streams so dB is stable
    seed_off = (int(seed) ^ 0xA53A0FF1 ^ (int(sep) << 1)) & 0xFFFFFFFFFFFFFFFF
    seed_on  = (int(seed) ^ 0xA53A0FF2 ^ (int(sep) << 1)) & 0xFFFFFFFFFFFFFFFF

    rng_off = np.random.default_rng(seed_off)
    rng_on  = np.random.default_rng(seed_on)

    sim_off = sim(tx_on=False, rng_local=rng_off)
    sim_on  = sim(tx_on=True,  rng_local=rng_on)

    dB1 = sim_on["meanB1"] - sim_off["meanB1"]
    dB2 = sim_on["meanB2"] - sim_off["meanB2"]

    return (sep, seed), {"dB1": dB1, "dB2": dB2, "W_total": float(sim_on["W_total"])}


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fast = os.environ.get("P9_FAST", "0").strip() not in ("0", "", "false", "False")
    jobs = int(os.environ.get("P9_JOBS", "1"))

    # lattice
    L = 4096
    N = 512
    xA = 2048 - N // 2
    dt = 0.01

    # DSSS params
    chip_spread = 64
    despread_box = 512
    chips_per_block = despread_box // chip_spread  # 8

    # FAST vs full
    if fast:
        steps_raw = 16384  # 32 blocks
        seeds = [42, 43]
        separations = [1024]
        k_flips = [0, 4, 8]
        warmup_steps = 1024  # 2 blocks
    else:
        steps_raw = 65536  # 128 blocks
        seeds = [42, 43, 44, 45, 46]
        separations = [256, 512, 1024, 1536]
        k_flips = [0, 1, 2, 4, 8]
        warmup_steps = 2048  # 4 blocks

    steps = (steps_raw // despread_box) * despread_box
    nblocks = steps // despread_box

    warmup_steps = (warmup_steps // despread_box) * despread_box
    warmup_blocks = warmup_steps // despread_box
    warmup_blocks = int(min(warmup_blocks, max(1, nblocks // 8)))
    slb = slice(warmup_blocks, nblocks)

    # controller
    controller_on = True
    linear_controller = True
    k_fb = 2.5
    k_obs = 1.0
    u_max = 0.02
    k_diff = 2.0
    chi_boost = 0.15

    # fixed targets
    code = "ACG"

    # provenance: repo weights -> seed
    _, w_sha, w_path, w_raw = load_repo_bits(4096)
    base_seed = _seed_from_bytes(w_raw) ^ 0xA5A5_1234

    # messages: PRN but enforced low correlation post-warmup
    msg1_seed = (int(base_seed) ^ 0x1111_1111) & 0xFFFFFFFFFFFFFFFF
    msg2_seed = (int(base_seed) ^ 0x2222_2222) & 0xFFFFFFFFFFFFFFFF

    target_abs_corr = float(os.environ.get("P9_MSG_CORR_MAX", "0.05"))
    msg1_sym, msg2_sym, msg12_corr = make_lowcorr_pair_pm1(
        nblocks,
        seed1=int(msg1_seed),
        seed2=int(msg2_seed),
        warmup_blocks=int(warmup_blocks),
        target_abs_corr=target_abs_corr,
        max_tries=int(os.environ.get("P9_MSG_CORR_TRIES", "256")),
    )

    m1 = np.repeat(msg1_sym, despread_box)[:steps].astype(np.float64)
    m2 = np.repeat(msg2_sym, despread_box)[:steps].astype(np.float64)

    # chips
    walsh_row_1 = 1
    walsh_row_2 = 2
    chip1 = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_1)
    chip2 = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_2)

    inn12 = chip_block_inner(
        chip1,
        chip2,
        steps=steps,
        despread_box=despread_box,
        chips_per_block=chips_per_block,
        chip_spread=chip_spread,
    )
    chip_ortho = {
        "chip1_vs_chip2_inner_median": float(np.median(inn12[warmup_blocks:])),
        "chip1_vs_chip2_inner_maxabs": float(np.max(np.abs(inn12[warmup_blocks:]))),
        "definition": "per-block symbol inner product; Walsh rows are exactly orthogonal in the symbol basis",
    }

    # drive
    drive_amp = 0.010
    alpha = 0.75
    meas_noise_sigma = 2e-4

    run_id = f"P9_1{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P9_1_MUTM"

    # ----------------------------
    # PRECOMPUTE expensive sims ONCE per (sep,seed)
    # ----------------------------
    sim_params = {
        "L": L,
        "N": N,
        "xA": xA,
        "dt": dt,
        "steps": steps,
        "code": code,
        "controller_on": controller_on,
        "linear_controller": linear_controller,
        "k_fb": k_fb,
        "k_obs": k_obs,
        "u_max": u_max,
        "k_diff": k_diff,
        "chi_boost": chi_boost,
        "drive_amp": drive_amp,
        "alpha": alpha,
        "meas_noise_sigma": meas_noise_sigma,
        "m1": m1,
        "m2": m2,
        "chip1": chip1,
        "chip2": chip2,
        "despread_box": despread_box,
        "chip_spread": chip_spread,
        "chips_per_block": chips_per_block,
    }

    combos = [(int(sep), int(s)) for sep in separations for s in seeds]
    sim_cache: dict[tuple[int, int], dict] = {}

    if jobs > 1 and len(combos) > 1:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

        payloads = [{"sep": sep, "seed": s, "params": sim_params} for (sep, s) in combos]
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            futs = [ex.submit(_simulate_pair_worker, p) for p in payloads]
            for f in as_completed(futs):
                key, val = f.result()
                sim_cache[key] = val
    else:
        for sep, s in combos:
            key, val = _simulate_pair_worker({"sep": sep, "seed": s, "params": sim_params})
            sim_cache[key] = val

    # ----------------------------
    # results structure
    # ----------------------------
    results: dict = {
        "timestamp": utc_ts(),
        "run_id": run_id,
        "git_rev": git_rev(),
        "constants": const,
        "params": {
            "fast_mode": bool(fast),
            "jobs": int(jobs),
            "lattice_size": L,
            "window_len": N,
            "dt": dt,
            "steps_total": steps,
            "nblocks": nblocks,
            "warmup_blocks": warmup_blocks,
            "seeds": seeds,
            "separations": separations,
            "code": code,
            "controller": {
                "controller_on": controller_on,
                "linear_controller": linear_controller,
                "k_fb": k_fb,
                "k_obs": k_obs,
                "u_max": u_max,
            },
            "messages": {
                "type": "PRN ±1 (low-corr search)",
                "msg1_seed": int(msg1_seed),
                "msg2_seed_base": int(msg2_seed),
                "target_abs_corr": float(target_abs_corr),
                "max_tries": int(os.environ.get("P9_MSG_CORR_TRIES", "256")),
                "msg12_corr_after_warmup": float(msg12_corr),
            },
            "chip": {
                "type": "Walsh/Hadamard (symbol-level)",
                "chip_spread": chip_spread,
                "despread_box": despread_box,
                "chips_per_block": chips_per_block,
                "walsh_row_1": walsh_row_1,
                "walsh_row_2": walsh_row_2,
                "orthogonality": chip_ortho,
            },
            "multiplex": {
                "channels": 2,
                "drive": "baseband superposition (symbol-level Walsh)",
                "drive_amp": drive_amp,
                "alpha": alpha,
            },
            "mutation": {
                "k_flips": k_flips,
                "mutate": "receiver_key_only",
                "mutated_channel": 1,
                "definition": "flip sign of k chip-symbol segments per despread block on receiver chip for channel 1 only",
            },
            "repo_weights": {"path": w_path, "sha256": w_sha},
        },
        "by_k": {},
        "summary": {},
        "checks": {},
        "definitions": {
            "goal": "P9.1: corrupt ONE receiver key in the 2-channel multiplexer; only that channel should fail while the other remains high-fidelity; crosstalk stays low.",
            "non_claims": [
                "Engineered comms baseline; no biology/physics claims.",
                "Targets held identical; selectivity is chip/key-based by design.",
            ],
        },
    }

    # ----------------------------
    # cheap sweep over k (NO re-sim)
    # ----------------------------
    for k in k_flips:
        k_key = str(int(k))
        results["by_k"][k_key] = {"by_sep": {}, "aggregate": {}}

        for sep in separations:
            results["by_k"][k_key]["by_sep"][str(int(sep))] = {"per_seed": {}, "aggregate": {}}

            for s in seeds:
                cached = sim_cache[(int(sep), int(s))]
                dB1 = cached["dB1"]
                dB2 = cached["dB2"]

                mut_seed = (int(base_seed) ^ int(s) ^ (int(k) << 8) ^ int(sep)) & 0xFFFFFFFF
                chip1_rx = corrupt_receiver_chip_per_block(
                    chip1,
                    steps=steps,
                    despread_box=despread_box,
                    chips_per_block=chips_per_block,
                    chip_spread=chip_spread,
                    k_flip=int(k),
                    seed=int(mut_seed),
                )

                y11 = demod_blocks_baseband(dB1, chip1_rx, steps=steps, despread_box=despread_box)
                y22 = demod_blocks_baseband(dB2, chip2, steps=steps, despread_box=despread_box)

                rho11 = corr_safe(y11[slb], msg1_sym[slb])
                rho12 = corr_safe(y11[slb], msg2_sym[slb])
                rho22 = corr_safe(y22[slb], msg2_sym[slb])
                rho21 = corr_safe(y22[slb], msg1_sym[slb])

                results["by_k"][k_key]["by_sep"][str(int(sep))]["per_seed"][str(int(s))] = {
                    "rho11": float(rho11),
                    "rho12": float(rho12),
                    "rho22": float(rho22),
                    "rho21": float(rho21),
                    "W_total": float(cached["W_total"]),
                }

            def med(key: str) -> float:
                vals = [
                    results["by_k"][k_key]["by_sep"][str(int(sep))]["per_seed"][str(int(ss))][key]
                    for ss in seeds
                ]
                return float(np.median(np.asarray(vals, dtype=np.float64)))

            results["by_k"][k_key]["by_sep"][str(int(sep))]["aggregate"] = {
                "rho11_median": med("rho11"),
                "rho12_median": med("rho12"),
                "rho22_median": med("rho22"),
                "rho21_median": med("rho21"),
            }

        def med_over_seps(key: str) -> float:
            vals = [results["by_k"][k_key]["by_sep"][str(int(sep))]["aggregate"][key] for sep in separations]
            return float(np.median(np.asarray(vals, dtype=np.float64)))

        results["by_k"][k_key]["aggregate"] = {
            "rho11_median_over_seps": med_over_seps("rho11_median"),
            "rho12_median_over_seps": med_over_seps("rho12_median"),
            "rho22_median_over_seps": med_over_seps("rho22_median"),
            "rho21_median_over_seps": med_over_seps("rho21_median"),
        }

    def agg(k: int, key: str) -> float:
        return float(results["by_k"][str(int(k))]["aggregate"][key])

    k_mid = int(sorted(k_flips)[len(k_flips) // 2])
    k_max = int(sorted(k_flips)[-1])

    summary = {
        "msg12_corr_after_warmup": float(msg12_corr),
        "k0": {
            "rho11": agg(0, "rho11_median_over_seps"),
            "rho22": agg(0, "rho22_median_over_seps"),
            "rho12": agg(0, "rho12_median_over_seps"),
            "rho21": agg(0, "rho21_median_over_seps"),
        },
        "k_mid": {
            "k": k_mid,
            "rho11": agg(k_mid, "rho11_median_over_seps"),
            "rho22": agg(k_mid, "rho22_median_over_seps"),
            "rho12": agg(k_mid, "rho12_median_over_seps"),
            "rho21": agg(k_mid, "rho21_median_over_seps"),
        },
        "k_max": {
            "k": k_max,
            "rho11": agg(k_max, "rho11_median_over_seps"),
            "rho22": agg(k_max, "rho22_median_over_seps"),
            "rho12": agg(k_max, "rho12_median_over_seps"),
            "rho21": agg(k_max, "rho21_median_over_seps"),
        },
    }
    results["summary"] = summary

    # plots
    ks = np.asarray(k_flips, dtype=np.float64)
    r11 = np.asarray([agg(int(k), "rho11_median_over_seps") for k in k_flips], dtype=np.float64)
    r22 = np.asarray([agg(int(k), "rho22_median_over_seps") for k in k_flips], dtype=np.float64)
    r12 = np.asarray([agg(int(k), "rho12_median_over_seps") for k in k_flips], dtype=np.float64)
    r21 = np.asarray([agg(int(k), "rho21_median_over_seps") for k in k_flips], dtype=np.float64)

    plt.figure(figsize=(10, 4))
    plt.plot(ks, r11, marker="o", label="rho11 (Ch1 decode w/ mutated K1)")
    plt.plot(ks, r22, marker="o", label="rho22 (Ch2 decode w/ correct K2)")
    plt.axhline(0.0, linewidth=1)
    plt.xlabel("k flips per block (receiver key for channel 1)")
    plt.ylabel("median corr over separations")
    plt.title("P9.1 Mutation-in-Multi: only the mutated channel should fail")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_main = OUT_DIR / "PAEV_P9_1_MutationInMulti_MainRho_vs_k.png"
    plt.savefig(p_png_main, dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(ks, np.abs(r12), marker="o", label="|rho12| (crosstalk into Ch1 decode)")
    plt.plot(ks, np.abs(r21), marker="o", label="|rho21| (crosstalk into Ch2 decode)")
    plt.xlabel("k flips per block (receiver key for channel 1)")
    plt.ylabel("median |corr| over separations")
    plt.title("P9.1 Mutation-in-Multi: crosstalk vs k")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_xt = OUT_DIR / "PAEV_P9_1_MutationInMulti_CrosstalkAbsRho_vs_k.png"
    plt.savefig(p_png_xt, dpi=200)
    plt.close()

    # checks
    min_abs_main = 0.25
    max_abs_xtalk = float(os.environ.get("P9_MAX_XTALK", "0.18" if fast else "0.15"))
    max_abs_msg12_corr = float(target_abs_corr)
    max_abs_rho11_kmid = 0.15
    min_abs_rho22_kmid = 0.80
    inv_tol = 0.20
    ortho_warn = 0.25

    abs_r11_k0 = abs(summary["k0"]["rho11"])
    abs_r22_k0 = abs(summary["k0"]["rho22"])
    abs_r12_k0 = abs(summary["k0"]["rho12"])
    abs_r21_k0 = abs(summary["k0"]["rho21"])

    abs_r11_km = abs(summary["k_mid"]["rho11"])
    abs_r22_km = abs(summary["k_mid"]["rho22"])
    abs_r12_km = abs(summary["k_mid"]["rho12"])
    abs_r21_km = abs(summary["k_mid"]["rho21"])

    r11_kmax = float(summary["k_max"]["rho11"])
    r11_k0 = float(summary["k0"]["rho11"])

    ok = True
    ok &= (abs(float(msg12_corr)) <= max_abs_msg12_corr)

    ok &= (abs_r11_k0 >= min_abs_main)
    ok &= (abs_r22_k0 >= min_abs_main)
    ok &= (abs_r12_k0 <= max_abs_xtalk)
    ok &= (abs_r21_k0 <= max_abs_xtalk)

    ok &= (abs_r11_km <= max_abs_rho11_kmid)
    ok &= (abs_r22_km >= min_abs_rho22_kmid)

    ok &= (abs_r12_km <= max_abs_xtalk)
    ok &= (abs_r21_km <= max_abs_xtalk)

    inv_ok = (abs(r11_kmax + r11_k0) <= inv_tol)
    orth_ok = (abs(chip_ortho["chip1_vs_chip2_inner_maxabs"]) <= ortho_warn)

    results["checks"] = {
        "overall_pass": bool(ok),
        "orthogonality_ok": bool(orth_ok),
        "inversion_ok": bool(inv_ok),
        "criteria": {
            "min_abs_main": min_abs_main,
            "max_abs_crosstalk": max_abs_xtalk,
            "max_abs_msg12_corr": max_abs_msg12_corr,
            "max_abs_rho11_kmid": max_abs_rho11_kmid,
            "min_abs_rho22_kmid": min_abs_rho22_kmid,
            "inv_tol": inv_tol,
            "chip1_vs_chip2_ortho_warn_thresh": ortho_warn,
        },
        "observed": {
            "msg12_corr_after_warmup": float(msg12_corr),
            "k0": results["summary"]["k0"],
            "k_mid": results["summary"]["k_mid"],
            "k_max": results["summary"]["k_max"],
            "chip1_vs_chip2_inner_median": float(chip_ortho["chip1_vs_chip2_inner_median"]),
            "chip1_vs_chip2_inner_maxabs": float(chip_ortho["chip1_vs_chip2_inner_maxabs"]),
        },
    }

    out_json = OUT_DIR / "P9_1_mutation_in_multi.json"
    out_json.write_text(json.dumps(results, indent=2) + "\n")

    print("=== P9.1 — Mutation-in-Multi (Corrupt ONE Receiver Key) ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_png_main}")
    print(f"✅ PNG  -> {p_png_xt}")
    print(f"RUN_ID  -> {run_id}")
    print(f"MODE    -> fast={bool(fast)} jobs={jobs}")
    print(f"CHECKS  -> overall_pass={bool(ok)} | orthogonality_ok={bool(orth_ok)} | inversion_ok={bool(inv_ok)}")
    if not ok:
        print("Observed:", results["checks"]["observed"])
        print("Criteria:", results["checks"]["criteria"])


if __name__ == "__main__":
    main()