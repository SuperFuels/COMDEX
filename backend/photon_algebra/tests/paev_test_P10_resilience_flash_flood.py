# backend/photon_algebra/tests/paev_test_P10_resilience_flash_flood.py
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


def _csv_floats(env: str, default: list[float]) -> list[float]:
    s = os.environ.get(env, "").strip()
    if not s:
        return default
    out: list[float] = []
    for tok in s.split(","):
        tok = tok.strip()
        if tok:
            out.append(float(tok))
    return out if out else default


def _csv_ints(env: str, default: list[int]) -> list[int]:
    s = os.environ.get(env, "").strip()
    if not s:
        return default
    out: list[int] = []
    for tok in s.split(","):
        tok = tok.strip()
        if tok:
            out.append(int(tok))
    return out if out else default


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
# deterministic PRN message (block-aligned)
# ----------------------------
def prn_pm1(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    bits = rng.integers(0, 2, size=int(n), dtype=np.int64)
    return (2.0 * bits - 1.0).astype(np.float64)


def _pm1_not_degenerate(x: np.ndarray, sl: slice, *, min_std: float = 0.25) -> bool:
    """
    Reject "degenerate" block messages (e.g., all +1 after warmup) which make corr_safe() return 0.
    For pm1, std = sqrt(1-mean^2). Require std >= min_std on post-warmup slice.
    """
    y = np.asarray(x[sl], dtype=np.float64)
    if y.size < 8:
        # too short to be reliable; force longer runs instead of accepting pathological cases
        return False
    if np.std(y) < float(min_std):
        return False
    # also require both symbols appear
    if np.unique(y).size < 2:
        return False
    return True


def make_lowcorr_pair_pm1(
    nblocks: int,
    *,
    seed1: int,
    seed2: int,
    warmup_blocks: int,
    target_abs_corr: float,
    max_tries: int = 1024,
    min_std: float = 0.25,
) -> tuple[np.ndarray, np.ndarray, float, int]:
    """
    Deterministically choose msg2 so corr(msg1,msg2) over post-warmup blocks is <= target_abs_corr,
    while forbidding degenerate sequences (constant after warmup).
    Returns (msg1, msg2, corr, chosen_seed2).
    """
    msg1 = prn_pm1(nblocks, int(seed1))
    sl = slice(int(warmup_blocks), int(nblocks))

    if not _pm1_not_degenerate(msg1, sl, min_std=float(min_std)):
        # extremely unlikely, but keep the failure mode explicit.
        raise RuntimeError("msg1 became degenerate; increase blocks/steps or adjust seeds.")

    best_msg2: np.ndarray | None = None
    best_abs = 1e9
    best_corr = 0.0
    best_seed = int(seed2)

    MIX = 0x9E3779B97F4A7C15
    for i in range(int(max_tries)):
        s2 = (int(seed2) ^ int((i + 1) * MIX)) & 0xFFFFFFFFFFFFFFFF
        cand2 = prn_pm1(nblocks, int(s2))

        if not _pm1_not_degenerate(cand2, sl, min_std=float(min_std)):
            continue

        c = corr_safe(msg1[sl], cand2[sl])
        ac = abs(float(c))
        if ac < best_abs:
            best_abs = ac
            best_msg2 = cand2
            best_corr = float(c)
            best_seed = int(s2)
        if ac <= float(target_abs_corr):
            return msg1, cand2, float(c), int(s2)

    if best_msg2 is None:
        raise RuntimeError(
            "No non-degenerate msg2 found. Increase steps (more blocks) or raise P10_MSG_CORR_TRIES."
        )
    return msg1, best_msg2, float(best_corr), int(best_seed)


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
# glyph shaping = block-rate linear unmixing (2x2)
# ----------------------------
def estimate_mix_A(
    msg1_sym: np.ndarray,
    msg2_sym: np.ndarray,
    r1: np.ndarray,
    r2: np.ndarray,
    slb: slice,
) -> np.ndarray:
    X = np.stack([msg1_sym[slb], msg2_sym[slb]], axis=1)  # (nb,2)
    y1 = r1[slb]
    y2 = r2[slb]
    c1, *_ = np.linalg.lstsq(X, y1, rcond=None)
    c2, *_ = np.linalg.lstsq(X, y2, rcond=None)
    return np.array([[c1[0], c1[1]], [c2[0], c2[1]]], dtype=np.float64)


def unmix_messages(A: np.ndarray, r1: np.ndarray, r2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    r = np.stack([r1, r2], axis=0)
    try:
        invA = np.linalg.inv(A)
    except np.linalg.LinAlgError:
        invA = np.linalg.pinv(A)
    mhat = invA @ r
    return mhat[0], mhat[1]


# ----------------------------
# P10 "flash flood" burst interference
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


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fast = os.environ.get("P10_FAST", "0").strip() not in ("0", "", "false", "False")
    jobs_env = int(os.environ.get("P10_JOBS", "1"))  # recorded only

    # lattice
    L = 4096
    N = 512
    xA = 2048 - N // 2

    # time
    dt = 0.01

    # DSSS params
    chip_spread = 64
    despread_box = 512
    chips_per_block = despread_box // chip_spread  # 8

    # sweep config (FAST must still have enough blocks to avoid degenerate msg2 / chance correlations)
    if fast:
        steps_raw = int(os.environ.get("P10_FAST_STEPS_RAW", "16384"))  # 32 blocks (stable)
        seeds = _csv_ints("P10_FAST_SEEDS", [42, 43])
        separations = _csv_ints("P10_FAST_SEPS", [1024])
        warmup_steps = int(os.environ.get("P10_FAST_WARMUP_STEPS", "1024"))  # 2 blocks
        burst_amps = _csv_floats("P10_FAST_AMPS", [0.00, 0.01, 0.02])
        burst_widths = _csv_ints("P10_FAST_WIDTHS", [64, 256])
        burst_periods = _csv_ints("P10_FAST_PERIODS", [512, 1024])
    else:
        steps_raw = int(os.environ.get("P10_STEPS_RAW", "65536"))  # 128 blocks
        seeds = _csv_ints("P10_SEEDS", [42, 43, 44, 45, 46])
        separations = _csv_ints("P10_SEPS", [256, 512, 1024, 1536])
        warmup_steps = int(os.environ.get("P10_WARMUP_STEPS", "2048"))  # 4 blocks
        burst_amps = _csv_floats("P10_AMPS", [0.00, 0.005, 0.01, 0.02, 0.03, 0.04])
        burst_widths = _csv_ints("P10_WIDTHS", [16, 64, 256, 512])
        burst_periods = _csv_ints("P10_PERIODS", [128, 256, 512, 1024, 2048])

    steps = (steps_raw // despread_box) * despread_box
    nblocks = steps // despread_box

    warmup_steps = (warmup_steps // despread_box) * despread_box
    warmup_blocks = max(1, warmup_steps // despread_box)
    warmup_blocks = int(min(warmup_blocks, max(2, nblocks // 8)))  # keep >=2 blocks warmup when possible
    slb = slice(warmup_blocks, nblocks)

    # controller (keep linear)
    controller_on = True
    linear_controller = True
    k_fb = 2.5
    k_obs = 1.0
    u_max = 0.02  # recorded
    k_diff = 2.0
    chi_boost = 0.15

    # targets (identical)
    code = "ACG"

    # provenance seed
    _, w_sha, w_path, w_raw = load_repo_bits(4096)
    base_seed = _seed_from_bytes(w_raw) ^ 0xA5A5_1234

    # messages: PRN but low-corr enforced post-warmup, non-degenerate
    msg1_seed = (int(base_seed) ^ 0x1111_1111) & 0xFFFFFFFFFFFFFFFF
    msg2_seed_base = (int(base_seed) ^ 0x2222_2222) & 0xFFFFFFFFFFFFFFFF
    target_abs_corr = float(os.environ.get("P10_MSG_CORR_MAX", "0.05"))
    msg1_sym, msg2_sym, msg12_corr, msg2_seed_chosen = make_lowcorr_pair_pm1(
        nblocks,
        seed1=int(msg1_seed),
        seed2=int(msg2_seed_base),
        warmup_blocks=int(warmup_blocks),
        target_abs_corr=float(target_abs_corr),
        max_tries=int(os.environ.get("P10_MSG_CORR_TRIES", "1024")),
        min_std=float(os.environ.get("P10_MSG_MIN_STD", "0.25")),
    )

    m1 = np.repeat(msg1_sym, despread_box)[:steps].astype(np.float64)
    m2 = np.repeat(msg2_sym, despread_box)[:steps].astype(np.float64)

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
        "definition": "per-block mean-symbol inner product; should be ~0 for orthogonal Walsh rows",
    }

    drive_amp = 0.010
    alpha = 0.75
    meas_noise_sigma = 2e-4

    run_id = f"P10{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P10_FLOOD"

    def simulate(sep: int, mode: str, seed: int, burst: np.ndarray) -> dict:
        """
        mode:
          - "MOD_ON": normal multiplex
          - "MOD_OFF": no DSSS drive (control)
          - "WRONG_CHIPS": swap chip assignments at TX (control; RAW should swap)
        """
        rng = np.random.default_rng(int(seed))

        xB1 = int(np.clip(xA + int(sep), 0, L - N))
        xB2 = int(np.clip(xA - int(sep), 0, L - N))

        tgt = build_target(code, N)
        gmask = np.array([1.0 if code[i % len(code)] == "G" else 0.0 for i in range(N)], dtype=np.float64)

        x = np.zeros(L, dtype=np.float64)
        x[xA : xA + N] = tgt
        x[xB1 : xB1 + N] = tgt
        x[xB2 : xB2 + N] = tgt
        x += rng.normal(0.0, 1e-6, size=L)

        meanB1 = np.zeros(steps, dtype=np.float64)
        meanB2 = np.zeros(steps, dtype=np.float64)

        W_fb = W_obs = W_drive = W_burst = 0.0

        for t in range(steps):
            lap = laplacian(x)

            wA = x[xA : xA + N]
            wB1 = x[xB1 : xB1 + N]
            wB2 = x[xB2 : xB2 + N]

            if mode == "MOD_ON":
                drive_scalar = drive_amp * (alpha * (m1[t] * chip1[t] + m2[t] * chip2[t]))
            elif mode == "WRONG_CHIPS":
                drive_scalar = drive_amp * (alpha * (m1[t] * chip2[t] + m2[t] * chip1[t]))
            else:
                drive_scalar = 0.0

            bt = float(burst[t])
            W_drive += float(L) * float(drive_scalar * drive_scalar)
            W_burst += float(L) * float(bt * bt)

            if controller_on:
                eA = tgt - wA
                eB1 = tgt - wB1
                eB2 = tgt - wB2

                # linear controller
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

            # shared medium carries drive + burst
            x += (drive_scalar + bt)

            W_fb += float(np.sum(uA_fb * uA_fb) + np.sum(uB1_fb * uB1_fb) + np.sum(uB2_fb * uB2_fb))
            W_obs += float(np.sum(uA_ob * uA_ob) + np.sum(uB1_ob * uB1_ob) + np.sum(uB2_ob * uB2_ob))

            meanB1[t] = float(np.mean(x[xB1 : xB1 + N])) + float(rng.normal(0.0, meas_noise_sigma))
            meanB2[t] = float(np.mean(x[xB2 : xB2 + N])) + float(rng.normal(0.0, meas_noise_sigma))

        return {
            "meanB1": meanB1,
            "meanB2": meanB2,
            "W_feedback": float(W_fb),
            "W_observer": float(W_obs),
            "W_drive": float(W_drive),
            "W_burst": float(W_burst),
            "W_total": float(W_fb + W_obs + W_drive + W_burst),
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
                "k_diff": k_diff,
                "chi_boost": chi_boost,
                "note": "linear_controller=True avoids nonlinear distortion products.",
            },
            "messages": {
                "type": "PRN ±1 (low-corr + non-degenerate enforced)",
                "msg1_seed": int(msg1_seed),
                "msg2_seed_base": int(msg2_seed_base),
                "msg2_seed_chosen": int(msg2_seed_chosen),
                "target_abs_corr": float(target_abs_corr),
                "max_tries": int(os.environ.get("P10_MSG_CORR_TRIES", "1024")),
                "min_std_post_warmup": float(os.environ.get("P10_MSG_MIN_STD", "0.25")),
                "msg12_corr_after_warmup": float(msg12_corr),
            },
            "chip": {
                "type": "Walsh/Hadamard",
                "chip_spread": chip_spread,
                "despread_box": despread_box,
                "chips_per_block": chips_per_block,
                "walsh_row_1": walsh_row_1,
                "walsh_row_2": walsh_row_2,
                "orthogonality": chip_ortho,
            },
            "multiplex": {
                "channels": 2,
                "drive": "baseband superposition",
                "drive_amp": drive_amp,
                "alpha": alpha,
                "glyph_shaping": {
                    "enabled": True,
                    "method": "block-rate 2x2 decorrelating detector (estimate A via least squares; invert A)",
                    "note": "Used for MOD_ON scoring. Controls validate RAW keying behavior.",
                },
            },
            "flash_flood": {
                "definition": "Additive global burst interference b(t): rectangular bursts every period steps of width W and amplitude A.",
                "amps": burst_amps,
                "widths_steps": burst_widths,
                "periods_steps": burst_periods,
                "phase_rule": "phase = (seed xor sep xor (width<<8) xor (period<<16)) % period",
                "baseline_rule": "Subtract a NO-BURST MOD_OFF reference so burst energy remains as interference in dB(t).",
            },
            "repo_weights": {"path": w_path, "sha256": w_sha},
        },
        "grid": {},
        "boundary": {},
        "summary": {},
        "checks": {},
        "definitions": {
            "goal": "P10 resilience gateway: extend P9 multiplexing with structured burst interference; map pass-rate and resilience boundary under negative controls.",
            "non_claims": [
                "Engineered comms baseline; no biology/physics claims.",
                "Unmixing is part of the engineered MOD_ON receiver definition.",
                "Controls validate keying at the RAW matched-filter layer (pre-demix).",
            ],
        },
    }

    # ----------------------------
    # thresholds
    # ----------------------------
    min_abs_main = float(os.environ.get("P10_MIN_MAIN", "0.25"))
    max_abs_xtalk = float(os.environ.get("P10_MAX_XTALK", "0.18" if fast else "0.15"))
    max_abs_msg12_corr = float(target_abs_corr)

    # controls (RAW)
    max_fail_floor_raw = float(os.environ.get("P10_FAIL_FLOOR", "0.15"))
    min_swap_hit_raw = float(os.environ.get("P10_SWAP_HIT", "0.75"))

    ortho_warn = 0.25
    ok_ortho = (abs(chip_ortho["chip1_vs_chip2_inner_maxabs"]) <= ortho_warn)

    modes = ["MOD_ON", "MOD_OFF", "WRONG_CHIPS"]

    # PRECOMPUTE NO-BURST MOD_OFF baselines (huge speed win; also makes bursts not cancel)
    zero_burst = np.zeros(steps, dtype=np.float64)
    baseline: dict[tuple[int, int], dict] = {}
    for sep in separations:
        for s in seeds:
            baseline[(int(sep), int(s))] = simulate(sep=int(sep), mode="MOD_OFF", seed=int(s), burst=zero_burst)

    # for boundary: pass requires MOD_ON pass AND controls ok
    pass_flags_mod_on: dict[tuple[int, int, float], bool] = {}
    ctrl_ok_flags: dict[tuple[int, int, float], bool] = {}

    total_grid = len(burst_widths) * len(burst_periods) * len(burst_amps)
    grid_idx = 0

    for width in burst_widths:
        for period in burst_periods:
            for amp in burst_amps:
                grid_idx += 1
                if fast:
                    print(f"[P10] grid {grid_idx}/{total_grid}: width={int(width)} period={int(period)} amp={float(amp):g}")

                key = f"w{int(width)}_p{int(period)}_a{float(amp):.6g}"
                results["grid"][key] = {
                    "burst": {"amp": float(amp), "width_steps": int(width), "period_steps": int(period)},
                    "by_mode": {},
                    "aggregate": {},
                }

                mode_agg: dict[str, dict] = {}

                for mode in modes:
                    per_sep = {}
                    for sep in separations:
                        per_seed = {}

                        for s in seeds:
                            phase = int((int(s) ^ int(sep) ^ (int(width) << 8) ^ (int(period) << 16)) % int(period))
                            burst = burst_train_rect(steps, amp=float(amp), width=int(width), period=int(period), phase=phase)

                            sim_ref = baseline[(int(sep), int(s))]  # NO-BURST reference
                            sim_cur = simulate(sep=int(sep), mode=str(mode), seed=int(s), burst=burst)

                            dB1 = sim_cur["meanB1"] - sim_ref["meanB1"]
                            dB2 = sim_cur["meanB2"] - sim_ref["meanB2"]

                            r1 = demod_blocks_baseband(dB1, chip1, steps=steps, despread_box=despread_box)
                            r2 = demod_blocks_baseband(dB2, chip2, steps=steps, despread_box=despread_box)

                            # RAW correlations
                            rho11_raw = corr_safe(r1[slb], msg1_sym[slb])
                            rho12_raw = corr_safe(r1[slb], msg2_sym[slb])
                            rho22_raw = corr_safe(r2[slb], msg2_sym[slb])
                            rho21_raw = corr_safe(r2[slb], msg1_sym[slb])

                            # post-demix (MOD_ON scoring; recorded for all)
                            A = estimate_mix_A(msg1_sym, msg2_sym, r1, r2, slb=slb)
                            m1_hat, m2_hat = unmix_messages(A, r1, r2)

                            rho11 = corr_safe(m1_hat[slb], msg1_sym[slb])
                            rho12 = corr_safe(m1_hat[slb], msg2_sym[slb])
                            rho22 = corr_safe(m2_hat[slb], msg2_sym[slb])
                            rho21 = corr_safe(m2_hat[slb], msg1_sym[slb])

                            per_seed[str(int(s))] = {
                                "rho11": float(rho11),
                                "rho22": float(rho22),
                                "rho12": float(rho12),
                                "rho21": float(rho21),
                                "rho11_raw": float(rho11_raw),
                                "rho22_raw": float(rho22_raw),
                                "rho12_raw": float(rho12_raw),
                                "rho21_raw": float(rho21_raw),
                                "mix_A_T": A.T.tolist(),
                                "W_total": float(sim_cur["W_total"]),
                                "W_burst": float(sim_cur["W_burst"]),
                                "burst_phase": int(phase),
                            }

                        def med_seed(k: str) -> float:
                            vals = [per_seed[str(int(ss))][k] for ss in seeds]
                            return float(np.median(np.asarray(vals, dtype=np.float64)))

                        per_sep[str(int(sep))] = {
                            "per_seed": per_seed,
                            "aggregate": {
                                "rho11_median": med_seed("rho11"),
                                "rho22_median": med_seed("rho22"),
                                "rho12_median": med_seed("rho12"),
                                "rho21_median": med_seed("rho21"),
                                "rho11_raw_median": med_seed("rho11_raw"),
                                "rho22_raw_median": med_seed("rho22_raw"),
                                "rho12_raw_median": med_seed("rho12_raw"),
                                "rho21_raw_median": med_seed("rho21_raw"),
                            },
                        }

                    def med_over_seps(key2: str) -> float:
                        vals = [per_sep[str(int(sep))]["aggregate"][key2] for sep in separations]
                        return float(np.median(np.asarray(vals, dtype=np.float64)))

                    mode_agg[mode] = {
                        "rho11_median_over_seps": med_over_seps("rho11_median"),
                        "rho22_median_over_seps": med_over_seps("rho22_median"),
                        "rho12_median_over_seps": med_over_seps("rho12_median"),
                        "rho21_median_over_seps": med_over_seps("rho21_median"),
                        "rho11_raw_median_over_seps": med_over_seps("rho11_raw_median"),
                        "rho22_raw_median_over_seps": med_over_seps("rho22_raw_median"),
                        "rho12_raw_median_over_seps": med_over_seps("rho12_raw_median"),
                        "rho21_raw_median_over_seps": med_over_seps("rho21_raw_median"),
                    }

                    results["grid"][key]["by_mode"][mode] = {"by_sep": per_sep, "aggregate": mode_agg[mode]}

                def absf(x: float) -> float:
                    return abs(float(x))

                mo = mode_agg["MOD_ON"]
                off = mode_agg["MOD_OFF"]
                wr = mode_agg["WRONG_CHIPS"]

                # MOD_ON pass criteria (POST-DEMIX)
                mod_on_pass = True
                mod_on_pass &= (abs(float(msg12_corr)) <= max_abs_msg12_corr)
                mod_on_pass &= (absf(mo["rho11_median_over_seps"]) >= min_abs_main)
                mod_on_pass &= (absf(mo["rho22_median_over_seps"]) >= min_abs_main)
                mod_on_pass &= (absf(mo["rho12_median_over_seps"]) <= max_abs_xtalk)
                mod_on_pass &= (absf(mo["rho21_median_over_seps"]) <= max_abs_xtalk)

                # Controls validated at RAW matched filter level:
                # 1) MOD_OFF: burst-only should not decode either message
                ctrl_ok = True
                ctrl_ok &= (absf(off["rho11_raw_median_over_seps"]) <= max_fail_floor_raw)
                ctrl_ok &= (absf(off["rho22_raw_median_over_seps"]) <= max_fail_floor_raw)

                # 2) WRONG_CHIPS: raw should swap (self low, cross high)
                ctrl_ok &= (absf(wr["rho11_raw_median_over_seps"]) <= max_fail_floor_raw)
                ctrl_ok &= (absf(wr["rho22_raw_median_over_seps"]) <= max_fail_floor_raw)
                ctrl_ok &= (absf(wr["rho12_raw_median_over_seps"]) >= min_swap_hit_raw)
                ctrl_ok &= (absf(wr["rho21_raw_median_over_seps"]) >= min_swap_hit_raw)

                results["grid"][key]["aggregate"] = {
                    "msg12_corr_after_warmup": float(msg12_corr),
                    "mod_on_pass": bool(mod_on_pass),
                    "controls_ok_raw": bool(ctrl_ok),
                }

                pass_flags_mod_on[(int(width), int(period), float(amp))] = bool(mod_on_pass)
                ctrl_ok_flags[(int(width), int(period), float(amp))] = bool(ctrl_ok)

    # boundary: max amp that passes AND controls ok
    boundary = {}
    for width in burst_widths:
        for period in burst_periods:
            ok_amps = []
            for amp in burst_amps:
                if pass_flags_mod_on[(int(width), int(period), float(amp))] and ctrl_ok_flags[(int(width), int(period), float(amp))]:
                    ok_amps.append(float(amp))
            boundary_key = f"w{int(width)}_p{int(period)}"
            boundary[boundary_key] = {
                "width_steps": int(width),
                "period_steps": int(period),
                "max_amp_passing": float(max(ok_amps)) if ok_amps else 0.0,
                "pass_count": int(len(ok_amps)),
                "total_amps": int(len(burst_amps)),
                "duty_cycle": float(int(width) / max(1, int(period))),
            }
    results["boundary"] = boundary

    pass_count = 0
    ctrl_ok_count = 0
    total = 0
    for width in burst_widths:
        for period in burst_periods:
            for amp in burst_amps:
                total += 1
                if pass_flags_mod_on[(int(width), int(period), float(amp))]:
                    pass_count += 1
                if ctrl_ok_flags[(int(width), int(period), float(amp))]:
                    ctrl_ok_count += 1

    results["summary"] = {
        "msg12_corr_after_warmup": float(msg12_corr),
        "grid_total": int(total),
        "mod_on_pass_total": int(pass_count),
        "controls_ok_raw_total": int(ctrl_ok_count),
        "boundary_points": int(len(boundary)),
    }

    # plots: boundary vs period
    plt.figure(figsize=(10, 4))
    periods_sorted = sorted(set(int(p) for p in burst_periods))
    for width in burst_widths:
        ys = []
        for period in periods_sorted:
            bk = f"w{int(width)}_p{int(period)}"
            ys.append(results["boundary"][bk]["max_amp_passing"])
        plt.plot(
            np.asarray(periods_sorted, dtype=np.float64),
            np.asarray(ys, dtype=np.float64),
            marker="o",
            label=f"width={int(width)}",
        )
    plt.xlabel("burst period (steps)")
    plt.ylabel("max burst amp passing")
    plt.title("P10 Resilience Boundary: max passing burst amplitude vs burst period")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_boundary = OUT_DIR / "PAEV_P10_Resilience_Boundary_vs_Period.png"
    plt.savefig(p_png_boundary, dpi=200)
    plt.close()

    # optional: boundary vs duty cycle
    plt.figure(figsize=(10, 4))
    for width in burst_widths:
        xs = []
        ys = []
        for period in periods_sorted:
            bk = f"w{int(width)}_p{int(period)}"
            xs.append(results["boundary"][bk]["duty_cycle"])
            ys.append(results["boundary"][bk]["max_amp_passing"])
        plt.plot(np.asarray(xs, dtype=np.float64), np.asarray(ys, dtype=np.float64), marker="o", label=f"width={int(width)}")
    plt.xlabel("duty = width/period")
    plt.ylabel("max burst amp passing")
    plt.title("P10 Resilience Boundary: max passing burst amplitude vs duty cycle")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_duty = OUT_DIR / "PAEV_P10_Resilience_Boundary_vs_Duty.png"
    plt.savefig(p_png_duty, dpi=200)
    plt.close()

    # pass heatmap (choose middle width)
    w_mid = int(sorted(burst_widths)[len(burst_widths) // 2])
    P = np.asarray(sorted(set(int(p) for p in burst_periods)), dtype=np.int64)
    Aamps = np.asarray(sorted(set(float(a) for a in burst_amps)), dtype=np.float64)
    Z = np.zeros((Aamps.size, P.size), dtype=np.float64)

    for j, period in enumerate(P):
        for i, amp in enumerate(Aamps):
            ok = pass_flags_mod_on[(w_mid, int(period), float(amp))] and ctrl_ok_flags[(w_mid, int(period), float(amp))]
            Z[i, j] = 1.0 if ok else 0.0

    plt.figure(figsize=(10, 4))
    plt.imshow(
        Z,
        aspect="auto",
        origin="lower",
        extent=[float(P.min()), float(P.max()), float(Aamps.min()), float(Aamps.max())],
    )
    plt.colorbar(label="pass (1) / fail (0)")
    plt.xlabel("burst period (steps)")
    plt.ylabel("burst amp")
    plt.title(f"P10 Pass Map (MOD_ON + RAW-controls) at width={w_mid} steps")
    plt.tight_layout()
    p_png_heat = OUT_DIR / "PAEV_P10_Resilience_PassRateHeatmap.png"
    plt.savefig(p_png_heat, dpi=200)
    plt.close()

    overall_ok = True
    overall_ok &= ok_ortho
    overall_ok &= (abs(float(msg12_corr)) <= max_abs_msg12_corr)
    overall_ok &= (pass_count > 0)    # must have at least one MOD_ON pass
    overall_ok &= (ctrl_ok_count > 0) # must have at least one control-ok point

    results["checks"] = {
        "overall_pass": bool(overall_ok),
        "orthogonality_ok": bool(ok_ortho),
        "criteria": {
            "min_abs_main_post_demix": float(min_abs_main),
            "max_abs_crosstalk_post_demix": float(max_abs_xtalk),
            "max_abs_msg12_corr": float(max_abs_msg12_corr),
            "max_fail_floor_controls_raw": float(max_fail_floor_raw),
            "min_swap_hit_controls_raw": float(min_swap_hit_raw),
            "chip1_vs_chip2_ortho_warn_thresh": float(ortho_warn),
            "require_some_pass_points": True,
            "require_some_control_ok_points": True,
        },
        "observed": {
            "msg12_corr_after_warmup": float(msg12_corr),
            "mod_on_pass_total": int(pass_count),
            "controls_ok_raw_total": int(ctrl_ok_count),
            "grid_total": int(total),
            "chip1_vs_chip2_inner_median": float(chip_ortho["chip1_vs_chip2_inner_median"]),
            "chip1_vs_chip2_inner_maxabs": float(chip_ortho["chip1_vs_chip2_inner_maxabs"]),
        },
    }

    out_json = OUT_DIR / "P10_resilience_flash_flood.json"
    out_json.write_text(json.dumps(results, indent=2) + "\n")

    print("=== P10 — Resilience Gateway (Flash Flood bursts) ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_png_boundary}")
    print(f"✅ PNG  -> {p_png_duty}")
    print(f"✅ PNG  -> {p_png_heat}")
    print(f"RUN_ID  -> {run_id}")
    print(f"MODE    -> fast={bool(fast)} jobs={int(jobs_env)}")
    print(f"CHECKS  -> overall_pass={bool(overall_ok)} | orthogonality_ok={bool(ok_ortho)}")
    if not overall_ok:
        print("Observed:", results["checks"]["observed"])
        print("Criteria:", results["checks"]["criteria"])


if __name__ == "__main__":
    main()