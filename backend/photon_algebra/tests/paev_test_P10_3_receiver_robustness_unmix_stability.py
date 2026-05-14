# /workspaces/COMDEX/backend/photon_algebra/tests/paev_test_P10_3_receiver_robustness_unmix_stability.py
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
# deterministic PRN messages (block-aligned)
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
) -> tuple[np.ndarray, np.ndarray, float, int]:
    """
    Deterministically choose msg2 so corr(msg1,msg2) over post-warmup blocks is <= target_abs_corr,
    or as small as possible (still deterministic).
    Returns (msg1, msg2, corr, chosen_seed2).
    """
    msg1 = prn_pm1(nblocks, int(seed1))
    sl = slice(int(warmup_blocks), int(nblocks))

    best = None
    best_abs = 1e9
    best_corr = 0.0
    best_seed = int(seed2)

    MIX = 0x9E3779B97F4A7C15
    for i in range(int(max_tries)):
        s2 = (int(seed2) ^ int((i + 1) * MIX)) & 0xFFFFFFFFFFFFFFFF
        cand2 = prn_pm1(nblocks, int(s2))
        c = corr_safe(msg1[sl], cand2[sl])
        ac = abs(float(c))
        if ac < best_abs:
            best_abs = ac
            best = cand2
            best_corr = float(c)
            best_seed = int(s2)
        if ac <= float(target_abs_corr):
            return msg1, cand2, float(c), int(s2)

    assert best is not None
    return msg1, best, float(best_corr), int(best_seed)


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
    H = hadamard(int(chips_per_block))
    r = int(row) % int(chips_per_block)
    base = H[r]
    one_block = np.repeat(base, int(chip_spread)).astype(np.float64)
    reps = int(np.ceil(int(steps) / one_block.size))
    return np.tile(one_block, reps)[: int(steps)]


def chip_block_inner(
    ch1: np.ndarray,
    ch2: np.ndarray,
    *,
    steps: int,
    despread_box: int,
    chips_per_block: int,
    chip_spread: int,
) -> np.ndarray:
    nb = int(steps) // int(despread_box)
    a = ch1[: nb * int(despread_box)].reshape(nb, int(despread_box))
    b = ch2[: nb * int(despread_box)].reshape(nb, int(despread_box))
    a_sym = a.reshape(nb, int(chips_per_block), int(chip_spread)).mean(axis=2)
    b_sym = b.reshape(nb, int(chips_per_block), int(chip_spread)).mean(axis=2)
    inn = np.sum(a_sym * b_sym, axis=1) / float(chips_per_block)
    return inn


def demod_blocks_baseband(time_series: np.ndarray, chip: np.ndarray, *, steps: int, despread_box: int) -> np.ndarray:
    y = np.asarray(time_series, dtype=np.float64)
    z = y[: int(steps)] * chip[: int(steps)]
    nb = int(steps) // int(despread_box)
    z = z[: nb * int(despread_box)].reshape(nb, int(despread_box))
    return np.mean(z, axis=1)


# ----------------------------
# unmixing
# ----------------------------
def estimate_mix_A(msg1_sym: np.ndarray, msg2_sym: np.ndarray, r1: np.ndarray, r2: np.ndarray, slb: slice) -> np.ndarray:
    X = np.stack([msg1_sym[slb], msg2_sym[slb]], axis=1)  # (nb,2)
    y1 = r1[slb]
    y2 = r2[slb]
    c1, *_ = np.linalg.lstsq(X, y1, rcond=None)
    c2, *_ = np.linalg.lstsq(X, y2, rcond=None)
    return np.array([[c1[0], c1[1]], [c2[0], c2[1]]], dtype=np.float64)


def estimate_mix_A_concat(
    msg1_sym: np.ndarray,
    msg2_sym: np.ndarray,
    r1_list: list[np.ndarray],
    r2_list: list[np.ndarray],
    slb: slice,
) -> np.ndarray:
    # concatenate blocks across runs for a single stable calibration A
    X = np.stack([msg1_sym[slb], msg2_sym[slb]], axis=1)  # (nb,2)
    X_big = np.concatenate([X for _ in r1_list], axis=0)
    y1_big = np.concatenate([r1[slb] for r1 in r1_list], axis=0)
    y2_big = np.concatenate([r2[slb] for r2 in r2_list], axis=0)
    c1, *_ = np.linalg.lstsq(X_big, y1_big, rcond=None)
    c2, *_ = np.linalg.lstsq(X_big, y2_big, rcond=None)
    return np.array([[c1[0], c1[1]], [c2[0], c2[1]]], dtype=np.float64)


def unmix_messages(A: np.ndarray, r1: np.ndarray, r2: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    r = np.stack([r1, r2], axis=0)
    try:
        invA = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        invA = np.linalg.pinv(A)
    mhat = invA @ r
    # cond(A) for provenance (pinv handles singular, but cond becomes inf)
    try:
        cA = float(np.linalg.cond(A))
    except Exception:
        cA = float("inf")
    return mhat[0], mhat[1], cA


# ----------------------------
# burst interference
# ----------------------------
def burst_train_rect(steps: int, *, amp: float, width: int, period: int, phase: int = 0) -> np.ndarray:
    steps = int(steps)
    out = np.zeros(steps, dtype=np.float64)
    if float(amp) <= 0.0 or int(width) <= 0 or int(period) <= 0:
        return out
    width_i = int(min(int(width), int(period)))
    phase_i = int(phase) % int(period)
    a = float(amp)
    for t0 in range(phase_i, steps, int(period)):
        out[t0 : min(t0 + width_i, steps)] = a
    return out


# ----------------------------
# main
# ----------------------------
def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fast = os.environ.get("P10_3_FAST", "0").strip() not in ("0", "", "false", "False")
    jobs_env = int(os.environ.get("P10_3_JOBS", "1"))  # recorded only

    # lattice
    L = 4096
    N = 512
    xA = 2048 - N // 2

    # time / DSSS
    dt = 0.01
    chip_spread = 64
    despread_box = 512
    chips_per_block = despread_box // chip_spread  # 8

    # run lengths
    if fast:
        steps_raw = 16384  # 32 blocks
        seeds = [42]
        separations = [1024]
        warmup_steps = 1024  # 2 blocks
    else:
        steps_raw = 65536  # 128 blocks
        seeds = [42, 43]
        separations = [512, 1024, 1536]
        warmup_steps = 2048  # 4 blocks

    steps = (steps_raw // despread_box) * despread_box
    nblocks = steps // despread_box
    warmup_steps = (warmup_steps // despread_box) * despread_box
    warmup_blocks = max(1, warmup_steps // despread_box)
    warmup_blocks = int(min(warmup_blocks, max(1, nblocks // 8)))
    slb = slice(warmup_blocks, nblocks)

    # controller baseline (keep linear)
    controller_on = True
    k_fb_base = 2.5
    k_obs_base = 1.0
    k_diff_base = 2.0
    chi_boost = 0.15

    # targets identical
    code = "ACG"
    tgt = build_target(code, N)
    gmask = np.array([1.0 if code[i % len(code)] == "G" else 0.0 for i in range(N)], dtype=np.float64)

    # provenance seed
    _, w_sha, w_path, w_raw = load_repo_bits(4096)
    base_seed = _seed_from_bytes(w_raw) ^ 0xA5A5_1234

    # messages: PRN but low-corr enforced post-warmup
    msg1_seed = (int(base_seed) ^ 0x1111_1111) & 0xFFFFFFFFFFFFFFFF
    msg2_seed = (int(base_seed) ^ 0x2222_2222) & 0xFFFFFFFFFFFFFFFF
    target_abs_corr = float(os.environ.get("P10_3_MSG_CORR_MAX", "0.05"))
    msg1_sym, msg2_sym, msg12_corr, msg2_seed_chosen = make_lowcorr_pair_pm1(
        nblocks,
        seed1=int(msg1_seed),
        seed2=int(msg2_seed),
        warmup_blocks=int(warmup_blocks),
        target_abs_corr=float(target_abs_corr),
        max_tries=int(os.environ.get("P10_3_MSG_CORR_TRIES", "256")),
    )

    m1 = np.repeat(msg1_sym, despread_box)[:steps].astype(np.float64)
    m2 = np.repeat(msg2_sym, despread_box)[:steps].astype(np.float64)

    # chips (2 users)
    walsh_row_1 = 1
    walsh_row_2 = 2
    chip1 = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_1)
    chip2 = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_2)

    inn12 = chip_block_inner(
        chip1, chip2,
        steps=steps, despread_box=despread_box,
        chips_per_block=chips_per_block, chip_spread=chip_spread
    )
    chip_ortho = {
        "chip1_vs_chip2_inner_median": float(np.median(inn12[warmup_blocks:])),
        "chip1_vs_chip2_inner_maxabs": float(np.max(np.abs(inn12[warmup_blocks:]))),
        "definition": "per-block mean-symbol inner product; should be ~0 for orthogonal Walsh rows",
    }

    # drive
    drive_amp = float(os.environ.get("P10_3_DRIVE_AMP", "0.010"))
    alpha = float(os.environ.get("P10_3_ALPHA", "0.75"))

    # thresholds (fixed across regimes)
    min_abs_main = float(os.environ.get("P10_3_MIN_MAIN", "0.25"))
    max_abs_xtalk = float(os.environ.get("P10_3_MAX_XTALK", "0.18" if fast else "0.15"))
    ortho_warn = float(os.environ.get("P10_3_ORTHO_WARN", "0.25"))

    # regimes: receiver must use SAME A_calib, SAME thresholds
    # (we still log per-regime A_hat drift as diagnostic)
    if fast:
        regimes = [
            dict(name="clean", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.0, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="bursts", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="meas_hi", meas_noise=1e-3, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="medium_hi", meas_noise=2e-4, medium_noise=5e-5, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="diff_low", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=0.75, k_fb=1.0, k_obs=1.0),
            dict(name="ctrl_hi", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.2, k_obs=1.2),
        ]
    else:
        regimes = [
            dict(name="clean", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.0, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="bursts", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="meas_med", meas_noise=6e-4, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="meas_hi", meas_noise=1.5e-3, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="medium_med", meas_noise=2e-4, medium_noise=2e-5, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="medium_hi", meas_noise=2e-4, medium_noise=6e-5, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.0, k_obs=1.0),
            dict(name="diff_low", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=0.75, k_fb=1.0, k_obs=1.0),
            dict(name="diff_hi", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.25, k_fb=1.0, k_obs=1.0),
            dict(name="ctrl_lo", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=0.8, k_obs=0.8),
            dict(name="ctrl_hi", meas_noise=2e-4, medium_noise=0.0, burst_amp=0.02, burst_w=256, burst_p=512, k_diff=1.0, k_fb=1.2, k_obs=1.2),
        ]

    run_id = f"P10_3{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P10_3_RX_ROBUST"

    def simulate(
        *,
        sep: int,
        seed: int,
        meas_noise_sigma: float,
        medium_noise_sigma: float,
        burst: np.ndarray,
        k_fb_scale: float,
        k_obs_scale: float,
        k_diff_scale: float,
        mode: str,
    ) -> dict:
        """
        mode:
          - "MOD_ON"  : multiplex drive
          - "MOD_OFF" : no drive (baseline)
        """
        rng = np.random.default_rng(int(seed))

        xB1 = int(np.clip(xA + int(sep), 0, L - N))
        xB2 = int(np.clip(xA - int(sep), 0, L - N))

        x = np.zeros(L, dtype=np.float64)
        x[xA : xA + N] = tgt
        x[xB1 : xB1 + N] = tgt
        x[xB2 : xB2 + N] = tgt
        x += rng.normal(0.0, 1e-6, size=L)

        meanB1 = np.zeros(steps, dtype=np.float64)
        meanB2 = np.zeros(steps, dtype=np.float64)

        k_fb = k_fb_base * float(k_fb_scale)
        k_obs = k_obs_base * float(k_obs_scale)
        k_diff = k_diff_base * float(k_diff_scale)

        W_fb = W_obs = W_drive = W_burst = W_medium = 0.0

        for t in range(steps):
            lap = laplacian(x)

            wA = x[xA : xA + N]
            wB1 = x[xB1 : xB1 + N]
            wB2 = x[xB2 : xB2 + N]

            if mode == "MOD_ON":
                drive_scalar = drive_amp * (alpha * (m1[t] * chip1[t] + m2[t] * chip2[t]))
            else:
                drive_scalar = 0.0

            bt = float(burst[t])
            W_drive += float(L) * float(drive_scalar * drive_scalar)
            W_burst += float(L) * float(bt * bt)

            if controller_on:
                eA = tgt - wA
                eB1 = tgt - wB1
                eB2 = tgt - wB2

                uA_fb = k_fb * eA
                uA_ob = k_obs * eA
                uB1_fb = k_fb * eB1
                uB1_ob = k_obs * eB1
                uB2_fb = k_fb * eB2
                uB2_ob = k_obs * eB2
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

            # shared medium: drive + bursts + optional medium noise
            x += (drive_scalar + bt)
            if float(medium_noise_sigma) > 0.0:
                mn = float(rng.normal(0.0, float(medium_noise_sigma)))
                x += mn
                W_medium += float(L) * float(mn * mn)

            W_fb += float(np.sum(uA_fb * uA_fb) + np.sum(uB1_fb * uB1_fb) + np.sum(uB2_fb * uB2_fb))
            W_obs += float(np.sum(uA_ob * uA_ob) + np.sum(uB1_ob * uB1_ob) + np.sum(uB2_ob * uB2_ob))

            meanB1[t] = float(np.mean(x[xB1 : xB1 + N])) + float(rng.normal(0.0, float(meas_noise_sigma)))
            meanB2[t] = float(np.mean(x[xB2 : xB2 + N])) + float(rng.normal(0.0, float(meas_noise_sigma)))

        return {
            "meanB1": meanB1,
            "meanB2": meanB2,
            "W_feedback": float(W_fb),
            "W_observer": float(W_obs),
            "W_drive": float(W_drive),
            "W_burst": float(W_burst),
            "W_medium": float(W_medium),
            "W_total": float(W_fb + W_obs + W_drive + W_burst + W_medium),
        }

    # ----------------------------
    # calibration: build ONE fixed A_calib on clean regime (no bursts, low noise)
    # ----------------------------
    calib_reg = next(r for r in regimes if r["name"] == "clean")
    r1_list: list[np.ndarray] = []
    r2_list: list[np.ndarray] = []
    for sep in separations:
        for s in seeds:
            phase = int((int(s) ^ int(sep) ^ (int(calib_reg["burst_w"]) << 8) ^ (int(calib_reg["burst_p"]) << 16)) % int(calib_reg["burst_p"]))
            burst = burst_train_rect(
                steps,
                amp=float(calib_reg["burst_amp"]),
                width=int(calib_reg["burst_w"]),
                period=int(calib_reg["burst_p"]),
                phase=phase,
            )
            sim_off = simulate(
                sep=int(sep),
                seed=int(s),
                meas_noise_sigma=float(calib_reg["meas_noise"]),
                medium_noise_sigma=float(calib_reg["medium_noise"]),
                burst=burst,
                k_fb_scale=float(calib_reg["k_fb"]),
                k_obs_scale=float(calib_reg["k_obs"]),
                k_diff_scale=float(calib_reg["k_diff"]),
                mode="MOD_OFF",
            )
            sim_on = simulate(
                sep=int(sep),
                seed=int(s),
                meas_noise_sigma=float(calib_reg["meas_noise"]),
                medium_noise_sigma=float(calib_reg["medium_noise"]),
                burst=burst,
                k_fb_scale=float(calib_reg["k_fb"]),
                k_obs_scale=float(calib_reg["k_obs"]),
                k_diff_scale=float(calib_reg["k_diff"]),
                mode="MOD_ON",
            )
            dB1 = sim_on["meanB1"] - sim_off["meanB1"]
            dB2 = sim_on["meanB2"] - sim_off["meanB2"]
            r1 = demod_blocks_baseband(dB1, chip1, steps=steps, despread_box=despread_box)
            r2 = demod_blocks_baseband(dB2, chip2, steps=steps, despread_box=despread_box)
            r1_list.append(r1)
            r2_list.append(r2)

    A_calib = estimate_mix_A_concat(msg1_sym, msg2_sym, r1_list, r2_list, slb=slb)
    _, _, condA_calib = unmix_messages(A_calib, r1_list[0], r2_list[0])  # cond only

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
            "steps_total": steps,
            "nblocks": nblocks,
            "warmup_blocks": warmup_blocks,
            "seeds": seeds,
            "separations": separations,
            "code": code,
            "controller": {
                "controller_on": controller_on,
                "k_fb_base": float(k_fb_base),
                "k_obs_base": float(k_obs_base),
                "k_diff_base": float(k_diff_base),
                "chi_boost": float(chi_boost),
                "note": "Linear controller only (no clipping); robustness is tested by sweeping gains/diffusion/noise, not changing receiver.",
            },
            "messages": {
                "type": "PRN ±1 (low-corr search)",
                "msg1_seed": int(msg1_seed),
                "msg2_seed_base": int(msg2_seed),
                "msg2_seed_chosen": int(msg2_seed_chosen),
                "target_abs_corr": float(target_abs_corr),
                "max_tries": int(os.environ.get("P10_3_MSG_CORR_TRIES", "256")),
                "msg12_corr_after_warmup": float(msg12_corr),
            },
            "chip": {
                "type": "Walsh/Hadamard",
                "chip_spread": int(chip_spread),
                "despread_box": int(despread_box),
                "chips_per_block": int(chips_per_block),
                "walsh_row_1": int(walsh_row_1),
                "walsh_row_2": int(walsh_row_2),
                "orthogonality": chip_ortho,
            },
            "multiplex": {
                "channels": 2,
                "drive_amp": float(drive_amp),
                "alpha": float(alpha),
            },
            "receiver": {
                "definition": "Fixed unmixing matrix A_calib is learned ONCE from clean regime and reused across all regimes. No retuning.",
                "A_calib_T": A_calib.T.tolist(),
                "condA_calib": float(condA_calib),
            },
            "regimes": regimes,
            "repo_weights": {"path": w_path, "sha256": w_sha},
        },
        "by_regime": {},
        "summary": {},
        "checks": {},
        "definitions": {
            "goal": "P10.3 receiver robustness: demonstrate one fixed receiver/unmix rule remains valid across noise/controller/diffusion regimes (no retuning).",
            "raw_mixing_diagnostics": "Always record RAW correlation matrix between despread r1/r2 and messages (rho11_raw,rho12_raw,rho21_raw,rho22_raw) plus per-regime A_hat drift and cond(A_hat).",
        },
    }

    # ----------------------------
    # evaluate regimes with fixed A_calib
    # ----------------------------
    ortho_ok = abs(float(chip_ortho["chip1_vs_chip2_inner_maxabs"])) <= float(ortho_warn)
    pass_regimes = 0

    for idx, reg in enumerate(regimes):
        name = str(reg["name"])
        results["by_regime"][name] = {"per_sep": {}, "aggregate": {}, "pass": False}

        for sep in separations:
            per_seed = {}
            for s in seeds:
                phase = int((int(s) ^ int(sep) ^ (int(reg["burst_w"]) << 8) ^ (int(reg["burst_p"]) << 16)) % int(reg["burst_p"]))
                burst = burst_train_rect(
                    steps,
                    amp=float(reg["burst_amp"]),
                    width=int(reg["burst_w"]),
                    period=int(reg["burst_p"]),
                    phase=phase,
                )

                sim_off = simulate(
                    sep=int(sep),
                    seed=int(s),
                    meas_noise_sigma=float(reg["meas_noise"]),
                    medium_noise_sigma=float(reg["medium_noise"]),
                    burst=burst,
                    k_fb_scale=float(reg["k_fb"]),
                    k_obs_scale=float(reg["k_obs"]),
                    k_diff_scale=float(reg["k_diff"]),
                    mode="MOD_OFF",
                )
                sim_on = simulate(
                    sep=int(sep),
                    seed=int(s),
                    meas_noise_sigma=float(reg["meas_noise"]),
                    medium_noise_sigma=float(reg["medium_noise"]),
                    burst=burst,
                    k_fb_scale=float(reg["k_fb"]),
                    k_obs_scale=float(reg["k_obs"]),
                    k_diff_scale=float(reg["k_diff"]),
                    mode="MOD_ON",
                )

                dB1 = sim_on["meanB1"] - sim_off["meanB1"]
                dB2 = sim_on["meanB2"] - sim_off["meanB2"]

                r1 = demod_blocks_baseband(dB1, chip1, steps=steps, despread_box=despread_box)
                r2 = demod_blocks_baseband(dB2, chip2, steps=steps, despread_box=despread_box)

                # RAW mixing diagnostics (pre-demix)
                rho11_raw = corr_safe(r1[slb], msg1_sym[slb])
                rho12_raw = corr_safe(r1[slb], msg2_sym[slb])
                rho21_raw = corr_safe(r2[slb], msg1_sym[slb])
                rho22_raw = corr_safe(r2[slb], msg2_sym[slb])

                # Fixed receiver unmix (no retuning)
                m1_hat, m2_hat, condA_used = unmix_messages(A_calib, r1, r2)

                rho11 = corr_safe(m1_hat[slb], msg1_sym[slb])
                rho12 = corr_safe(m1_hat[slb], msg2_sym[slb])
                rho21 = corr_safe(m2_hat[slb], msg1_sym[slb])
                rho22 = corr_safe(m2_hat[slb], msg2_sym[slb])

                # Per-regime A_hat drift diagnostic (NOT used for decoding)
                A_hat = estimate_mix_A(msg1_sym, msg2_sym, r1, r2, slb=slb)
                try:
                    condA_hat = float(np.linalg.cond(A_hat))
                except Exception:
                    condA_hat = float("inf")
                drift = float(np.linalg.norm(A_hat - A_calib) / (np.linalg.norm(A_calib) + 1e-12))

                per_seed[str(int(s))] = {
                    "rho11": float(rho11),
                    "rho22": float(rho22),
                    "rho12": float(rho12),
                    "rho21": float(rho21),
                    "rho11_raw": float(rho11_raw),
                    "rho12_raw": float(rho12_raw),
                    "rho21_raw": float(rho21_raw),
                    "rho22_raw": float(rho22_raw),
                    "A_hat_T": A_hat.T.tolist(),
                    "condA_hat": float(condA_hat),
                    "A_drift_rel": float(drift),
                    "condA_used": float(condA_used),
                    "W_total": float(sim_on["W_total"]),
                    "W_burst": float(sim_on["W_burst"]),
                    "W_medium": float(sim_on["W_medium"]),
                    "burst_phase": int(phase),
                }

            def med_seed(k: str) -> float:
                vals = [per_seed[str(int(ss))][k] for ss in seeds]
                return float(np.median(np.asarray(vals, dtype=np.float64)))

            results["by_regime"][name]["per_sep"][str(int(sep))] = {
                "per_seed": per_seed,
                "aggregate": {
                    "rho11_median": med_seed("rho11"),
                    "rho22_median": med_seed("rho22"),
                    "rho12_median": med_seed("rho12"),
                    "rho21_median": med_seed("rho21"),
                    "rho11_raw_median": med_seed("rho11_raw"),
                    "rho12_raw_median": med_seed("rho12_raw"),
                    "rho21_raw_median": med_seed("rho21_raw"),
                    "rho22_raw_median": med_seed("rho22_raw"),
                    "condA_hat_median": med_seed("condA_hat"),
                    "A_drift_rel_median": med_seed("A_drift_rel"),
                },
            }

        def med_over_seps(key2: str) -> float:
            vals = [results["by_regime"][name]["per_sep"][str(int(sep))]["aggregate"][key2] for sep in separations]
            return float(np.median(np.asarray(vals, dtype=np.float64)))

        agg = {
            "rho11_median_over_seps": med_over_seps("rho11_median"),
            "rho22_median_over_seps": med_over_seps("rho22_median"),
            "rho12_median_over_seps": med_over_seps("rho12_median"),
            "rho21_median_over_seps": med_over_seps("rho21_median"),
            "rho11_raw_median_over_seps": med_over_seps("rho11_raw_median"),
            "rho12_raw_median_over_seps": med_over_seps("rho12_raw_median"),
            "rho21_raw_median_over_seps": med_over_seps("rho21_raw_median"),
            "rho22_raw_median_over_seps": med_over_seps("rho22_raw_median"),
            "condA_hat_median_over_seps": med_over_seps("condA_hat_median"),
            "A_drift_rel_median_over_seps": med_over_seps("A_drift_rel_median"),
        }
        results["by_regime"][name]["aggregate"] = agg

        abs11 = abs(float(agg["rho11_median_over_seps"]))
        abs22 = abs(float(agg["rho22_median_over_seps"]))
        abs12 = abs(float(agg["rho12_median_over_seps"]))
        abs21 = abs(float(agg["rho21_median_over_seps"]))

        reg_pass = True
        reg_pass &= (abs(float(msg12_corr)) <= float(target_abs_corr))
        reg_pass &= (abs11 >= float(min_abs_main))
        reg_pass &= (abs22 >= float(min_abs_main))
        reg_pass &= (abs12 <= float(max_abs_xtalk))
        reg_pass &= (abs21 <= float(max_abs_xtalk))

        results["by_regime"][name]["pass"] = bool(reg_pass)
        if reg_pass:
            pass_regimes += 1

    # ----------------------------
    # summary + plots
    # ----------------------------
    reg_names = list(results["by_regime"].keys())
    min_main = []
    max_xt = []
    cond_hat = []
    drift = []
    pass_flags = []

    for rn in reg_names:
        a = results["by_regime"][rn]["aggregate"]
        min_main.append(min(abs(a["rho11_median_over_seps"]), abs(a["rho22_median_over_seps"])))
        max_xt.append(max(abs(a["rho12_median_over_seps"]), abs(a["rho21_median_over_seps"])))
        cond_hat.append(float(a["condA_hat_median_over_seps"]))
        drift.append(float(a["A_drift_rel_median_over_seps"]))
        pass_flags.append(1.0 if results["by_regime"][rn]["pass"] else 0.0)

    results["summary"] = {
        "msg12_corr_after_warmup": float(msg12_corr),
        "regimes_total": int(len(reg_names)),
        "regimes_passed": int(pass_regimes),
        "condA_calib": float(condA_calib),
    }

    # Plot 1: min main corr per regime
    plt.figure(figsize=(10, 4))
    plt.plot(np.arange(len(reg_names)), np.asarray(min_main, dtype=np.float64), marker="o", label="min |rho_ii| (post-demix, fixed A)")
    plt.axhline(float(min_abs_main), linestyle="--", label="min_abs_main")
    plt.xticks(np.arange(len(reg_names)), reg_names, rotation=20, ha="right")
    plt.ylabel("|correlation|")
    plt.title("P10.3 Receiver Robustness: min main correlation across regimes (fixed receiver)")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_main = OUT_DIR / "PAEV_P10_3_Robustness_MinMain_vs_Regime.png"
    plt.savefig(p_png_main, dpi=200)
    plt.close()

    # Plot 2: max crosstalk per regime
    plt.figure(figsize=(10, 4))
    plt.plot(np.arange(len(reg_names)), np.asarray(max_xt, dtype=np.float64), marker="o", label="max |rho_ij| (i≠j, post-demix, fixed A)")
    plt.axhline(float(max_abs_xtalk), linestyle="--", label="max_abs_xtalk")
    plt.xticks(np.arange(len(reg_names)), reg_names, rotation=20, ha="right")
    plt.ylabel("|correlation|")
    plt.title("P10.3 Receiver Robustness: max crosstalk across regimes (fixed receiver)")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_xt = OUT_DIR / "PAEV_P10_3_Robustness_MaxCrosstalk_vs_Regime.png"
    plt.savefig(p_png_xt, dpi=200)
    plt.close()

    # Plot 3: conditioning + drift (two curves, same axes)
    plt.figure(figsize=(10, 4))
    plt.plot(np.arange(len(reg_names)), np.asarray(cond_hat, dtype=np.float64), marker="o", label="median cond(A_hat)")
    plt.axhline(float(condA_calib), linestyle="--", label="cond(A_calib)")
    plt.xticks(np.arange(len(reg_names)), reg_names, rotation=20, ha="right")
    plt.ylabel("cond(A)")
    plt.title("P10.3 Receiver Robustness: demix conditioning drift across regimes")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_cond = OUT_DIR / "PAEV_P10_3_Robustness_CondAhat_vs_Regime.png"
    plt.savefig(p_png_cond, dpi=200)
    plt.close()

    # Plot 4: pass/fail strip
    plt.figure(figsize=(10, 1.8))
    plt.imshow(np.asarray([pass_flags], dtype=np.float64), aspect="auto", origin="lower", extent=[0, len(reg_names), 0, 1])
    plt.yticks([])
    plt.xticks(np.arange(len(reg_names)) + 0.5, reg_names, rotation=20, ha="right")
    plt.title("P10.3 Pass strip (1=pass, 0=fail)")
    plt.tight_layout()
    p_png_pass = OUT_DIR / "PAEV_P10_3_Robustness_PassStrip.png"
    plt.savefig(p_png_pass, dpi=200)
    plt.close()

    # ----------------------------
    # overall checks
    # ----------------------------
    overall_ok = True
    overall_ok &= bool(ortho_ok)
    overall_ok &= (abs(float(msg12_corr)) <= float(target_abs_corr))
    # robustness claim: ALL regimes in this test envelope must pass
    overall_ok &= (pass_regimes == len(reg_names))

    results["checks"] = {
        "overall_pass": bool(overall_ok),
        "orthogonality_ok": bool(ortho_ok),
        "criteria": {
            "min_abs_main_post_demix_fixed_receiver": float(min_abs_main),
            "max_abs_xtalk_post_demix_fixed_receiver": float(max_abs_xtalk),
            "max_abs_msg12_corr": float(target_abs_corr),
            "chip1_vs_chip2_ortho_warn_thresh": float(ortho_warn),
            "require_all_regimes_pass": True,
        },
        "observed": {
            "msg12_corr_after_warmup": float(msg12_corr),
            "regimes_passed": int(pass_regimes),
            "regimes_total": int(len(reg_names)),
            "condA_calib": float(condA_calib),
            "chip1_vs_chip2_inner_maxabs": float(chip_ortho["chip1_vs_chip2_inner_maxabs"]),
        },
    }

    out_json = OUT_DIR / "P10_3_receiver_robustness_unmix_stability.json"
    out_json.write_text(json.dumps(results, indent=2) + "\n")

    print("=== P10.3 — Receiver Robustness (Unmix Stability) ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_png_main}")
    print(f"✅ PNG  -> {p_png_xt}")
    print(f"✅ PNG  -> {p_png_cond}")
    print(f"✅ PNG  -> {p_png_pass}")
    print(f"RUN_ID  -> {run_id}")
    print(f"MODE    -> fast={bool(fast)} jobs={int(jobs_env)}")
    print(f"CHECKS  -> overall_pass={bool(overall_ok)} | regimes_passed={pass_regimes}/{len(reg_names)} | orthogonality_ok={bool(ortho_ok)}")
    if not overall_ok:
        print("Observed:", results["checks"]["observed"])
        print("Criteria:", results["checks"]["criteria"])


if __name__ == "__main__":
    main()