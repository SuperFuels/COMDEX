# backend/photon_algebra/tests/paev_test_P10_1_mutation_multi_resilience.py
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
) -> tuple[np.ndarray, np.ndarray, float, int]:
    msg1 = prn_pm1(nblocks, int(seed1))
    sl = slice(int(warmup_blocks), int(nblocks))

    best2 = None
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
            best2 = cand2
            best_corr = float(c)
            best_seed = int(s2)
        if ac <= float(target_abs_corr):
            return msg1, cand2, float(c), int(s2)

    assert best2 is not None
    return msg1, best2, float(best_corr), int(best_seed)


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


def demod_blocks_baseband(ts: np.ndarray, chip: np.ndarray, *, steps: int, despread_box: int) -> np.ndarray:
    y = np.asarray(ts, dtype=np.float64)[: int(steps)]
    z = y * chip[: int(steps)]
    nb = int(steps) // int(despread_box)
    return np.mean(z[: nb * int(despread_box)].reshape(nb, int(despread_box)), axis=1)


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


# ----------------------------
# RX-only key mutation (symbol-domain flips)
# ----------------------------
def mutate_chip_rx_symbolwise(
    chip: np.ndarray,
    *,
    steps: int,
    despread_box: int,
    chips_per_block: int,
    chip_spread: int,
    corrupt_frac: float,
    seed: int,
) -> np.ndarray:
    """
    Flip a fraction of chip symbols (±1) at the receiver only.
    Operates on (block, chip_symbol) grid so "frac" is meaningful.
    """
    if corrupt_frac <= 0.0:
        return chip.copy()

    nb = int(steps) // int(despread_box)
    # Extract symbol grid: (nb, chips_per_block) in ±1
    sym = chip[: nb * int(despread_box)].reshape(nb, int(chips_per_block), int(chip_spread)).mean(axis=2)
    sym = np.sign(sym)  # ±1
    sym[sym == 0.0] = 1.0

    rng = np.random.default_rng(int(seed))
    total = sym.size
    k = int(np.round(float(corrupt_frac) * float(total)))
    k = max(1, min(k, total))

    idx = rng.choice(total, size=k, replace=False)
    flat = sym.reshape(-1)
    flat[idx] *= -1.0
    sym2 = flat.reshape(nb, int(chips_per_block))

    # Re-expand to time chip
    blk = np.repeat(sym2, int(chip_spread), axis=1).reshape(nb, int(despread_box))
    out = blk.reshape(-1)
    # pad/trim to steps
    if out.size < int(steps):
        out = np.pad(out, (0, int(steps) - out.size), mode="edge")
    return out[: int(steps)].astype(np.float64)


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fast = os.environ.get("P10_1_FAST", "0").strip() not in ("0", "", "false", "False")
    jobs_env = int(os.environ.get("P10_1_JOBS", "1"))  # recorded only

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

    # sweep config
    if fast:
        steps_raw = 16384  # 32 blocks
        seeds = [42]
        separations = [1024]
        warmup_steps = 1024  # 2 blocks
        burst_amps = [0.00, 0.02]
        burst_widths = [64, 256]
        burst_periods = [512, 1024]
        corrupt_fracs = [0.0, 0.25, 0.5, 0.75]  # <-- stronger, adaptive
    else:
        steps_raw = 65536
        seeds = [42, 43, 44, 45, 46]
        separations = [256, 512, 1024, 1536]
        warmup_steps = 2048
        burst_amps = [0.00, 0.005, 0.01, 0.02, 0.03, 0.04]
        burst_widths = [16, 64, 256, 512]
        burst_periods = [128, 256, 512, 1024, 2048]
        corrupt_fracs = [0.0, 0.125, 0.25, 0.375, 0.5, 0.75]

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

    # targets
    code = "ACG"

    # provenance seed
    _, w_sha, w_path, w_raw = load_repo_bits(4096)
    base_seed = _seed_from_bytes(w_raw) ^ 0xA5A5_1234

    # messages
    msg1_seed = (int(base_seed) ^ 0x1111_1111) & 0xFFFFFFFFFFFFFFFF
    msg2_seed = (int(base_seed) ^ 0x2222_2222) & 0xFFFFFFFFFFFFFFFF
    target_abs_corr = float(os.environ.get("P10_MSG_CORR_MAX", "0.05"))
    msg1_sym, msg2_sym, msg12_corr, msg2_seed_chosen = make_lowcorr_pair_pm1(
        nblocks,
        seed1=int(msg1_seed),
        seed2=int(msg2_seed),
        warmup_blocks=int(warmup_blocks),
        target_abs_corr=float(target_abs_corr),
        max_tries=int(os.environ.get("P10_MSG_CORR_TRIES", "256")),
    )
    m1 = np.repeat(msg1_sym, despread_box)[:steps].astype(np.float64)
    m2 = np.repeat(msg2_sym, despread_box)[:steps].astype(np.float64)

    # chips (TX is clean)
    walsh_row_1 = 1
    walsh_row_2 = 2
    chip1 = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_1)
    chip2 = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_2)
    inn12 = chip_block_inner(
        chip1, chip2, steps=steps, despread_box=despread_box, chips_per_block=chips_per_block, chip_spread=chip_spread
    )
    chip_ortho = {
        "chip1_vs_chip2_inner_median": float(np.median(inn12[warmup_blocks:])),
        "chip1_vs_chip2_inner_maxabs": float(np.max(np.abs(inn12[warmup_blocks:]))),
    }

    # drive + noise
    drive_amp = 0.010
    alpha = 0.75
    meas_noise_sigma = 2e-4

    run_id = f"P10_1{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P10_1_MUT_MULTI"

    def simulate(sep: int, mode: str, seed: int, burst: np.ndarray) -> dict:
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

            x += (drive_scalar + bt)

            W_fb += float(np.sum(uA_fb * uA_fb) + np.sum(uB1_fb * uB1_fb) + np.sum(uB2_fb * uB2_fb))
            W_obs += float(np.sum(uA_ob * uA_ob) + np.sum(uB1_ob * uB1_ob) + np.sum(uB2_ob * uB2_ob))

            meanB1[t] = float(np.mean(x[xB1 : xB1 + N])) + float(rng.normal(0.0, meas_noise_sigma))
            meanB2[t] = float(np.mean(x[xB2 : xB2 + N])) + float(rng.normal(0.0, meas_noise_sigma))

        return {
            "meanB1": meanB1,
            "meanB2": meanB2,
            "W_total": float(W_fb + W_obs + W_drive + W_burst),
            "W_burst": float(W_burst),
        }

    # ----------------------------
    # thresholds
    # ----------------------------
    min_abs_main_clean_raw = float(os.environ.get("P10_1_MIN_MAIN", "0.25"))
    max_abs_xtalk_raw = float(os.environ.get("P10_1_MAX_XTALK", os.environ.get("P10_MAX_XTALK", "0.18")))
    max_drop_ratio = float(os.environ.get("P10_1_MAX_DROP_RATIO", "0.35"))
    max_delta_rho22 = float(os.environ.get("P10_1_MAX_DELTA_RHO22", "0.05"))
    ortho_warn = 0.25

    ok_ortho = abs(chip_ortho["chip1_vs_chip2_inner_maxabs"]) <= ortho_warn

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
            "messages": {
                "msg1_seed": int(msg1_seed),
                "msg2_seed_base": int(msg2_seed),
                "msg2_seed_chosen": int(msg2_seed_chosen),
                "target_abs_corr": float(target_abs_corr),
                "msg12_corr_after_warmup": float(msg12_corr),
            },
            "chip": {
                "chip_spread": chip_spread,
                "despread_box": despread_box,
                "chips_per_block": chips_per_block,
                "walsh_row_1": walsh_row_1,
                "walsh_row_2": walsh_row_2,
                "orthogonality": chip_ortho,
            },
            "flash_flood": {
                "amps": burst_amps,
                "widths_steps": burst_widths,
                "periods_steps": burst_periods,
                "phase_rule": "phase = (seed xor sep xor (width<<8) xor (period<<16)) % period",
            },
            "mutation": {
                "definition": "Receiver-1 key mutation (RX-only): flip a fraction of chip-symbols in K1 at the receiver.",
                "corrupt_fracs": corrupt_fracs,
                "note": "Scoring is RAW matched-filter layer (key-level effect).",
            },
            "repo_weights": {"path": w_path, "sha256": w_sha},
        },
        "grid": {},
        "summary": {},
        "checks": {},
        "definitions": {
            "goal": "P10.1: under bursts, corrupt ONLY receiver-1 key; show channel-1 decode collapses while channel-2 remains stable (isolation).",
            "non_claims": ["Engineered comms baseline; no biology/physics claims."],
        },
    }

    total_grid = len(burst_widths) * len(burst_periods) * len(burst_amps)
    gi = 0
    pass_points = 0

    # For plotting: store chosen drop_ratio per point
    drop_plot_rows = []

    for width in burst_widths:
        for period in burst_periods:
            for amp in burst_amps:
                gi += 1
                if fast:
                    print(f"[P10.1] grid {gi}/{total_grid}: width={int(width)} period={int(period)} amp={float(amp):g}")

                key = f"w{int(width)}_p{int(period)}_a{float(amp):.6g}"
                results["grid"][key] = {
                    "burst": {"amp": float(amp), "width_steps": int(width), "period_steps": int(period)},
                    "by_corrupt_frac": {},
                    "aggregate": {},
                }

                # Evaluate each corrupt_frac, then choose minimal that meets collapse criterion.
                best_star = None

                for frac in corrupt_fracs:
                    samples = []
                    for sep in separations:
                        for s in seeds:
                            phase = int((int(s) ^ int(sep) ^ (int(width) << 8) ^ (int(period) << 16)) % int(period))
                            burst = burst_train_rect(steps, amp=float(amp), width=int(width), period=int(period), phase=phase)

                            sim_off = simulate(sep=int(sep), mode="MOD_OFF", seed=int(s), burst=burst)
                            sim_on = simulate(sep=int(sep), mode="MOD_ON", seed=int(s), burst=burst)

                            dB1 = sim_on["meanB1"] - sim_off["meanB1"]
                            dB2 = sim_on["meanB2"] - sim_off["meanB2"]

                            # Clean demod
                            r1_clean = demod_blocks_baseband(dB1, chip1, steps=steps, despread_box=despread_box)
                            r2_clean = demod_blocks_baseband(dB2, chip2, steps=steps, despread_box=despread_box)

                            rho11_clean = corr_safe(r1_clean[slb], msg1_sym[slb])
                            rho22_clean = corr_safe(r2_clean[slb], msg2_sym[slb])
                            rho12_clean = corr_safe(r1_clean[slb], msg2_sym[slb])
                            rho21_clean = corr_safe(r2_clean[slb], msg1_sym[slb])

                            # Mutate ONLY RX1 chip
                            mut_seed = int(base_seed ^ 0xC0FFEE ^ int(sep) ^ (int(width) << 8) ^ (int(period) << 16) ^ int(s))
                            chip1_mut = mutate_chip_rx_symbolwise(
                                chip1,
                                steps=steps,
                                despread_box=despread_box,
                                chips_per_block=chips_per_block,
                                chip_spread=chip_spread,
                                corrupt_frac=float(frac),
                                seed=mut_seed,
                            )
                            r1_mut = demod_blocks_baseband(dB1, chip1_mut, steps=steps, despread_box=despread_box)
                            r2_mut = r2_clean  # RX2 unchanged

                            rho11_mut = corr_safe(r1_mut[slb], msg1_sym[slb])
                            rho22_mut = corr_safe(r2_mut[slb], msg2_sym[slb])
                            rho12_mut = corr_safe(r1_mut[slb], msg2_sym[slb])
                            rho21_mut = rho21_clean

                            samples.append(
                                {
                                    "sep": int(sep),
                                    "seed": int(s),
                                    "burst_phase": int(phase),
                                    "rho11_clean": float(rho11_clean),
                                    "rho22_clean": float(rho22_clean),
                                    "rho12_clean": float(rho12_clean),
                                    "rho21_clean": float(rho21_clean),
                                    "rho11_mut": float(rho11_mut),
                                    "rho22_mut": float(rho22_mut),
                                    "rho12_mut": float(rho12_mut),
                                    "rho21_mut": float(rho21_mut),
                                    "W_total": float(sim_on["W_total"]),
                                    "W_burst": float(sim_on["W_burst"]),
                                }
                            )

                    # Aggregate (median abs over samples)
                    def med_abs(k: str) -> float:
                        vals = np.asarray([abs(ss[k]) for ss in samples], dtype=np.float64)
                        return float(np.median(vals))

                    rho11_clean_med = med_abs("rho11_clean")
                    rho22_clean_med = med_abs("rho22_clean")
                    rho12_clean_med = med_abs("rho12_clean")
                    rho21_clean_med = med_abs("rho21_clean")
                    rho11_mut_med = med_abs("rho11_mut")
                    rho22_mut_med = med_abs("rho22_mut")

                    drop_ratio = float(rho11_mut_med / (rho11_clean_med + 1e-12))
                    delta_rho22 = float(abs(rho22_mut_med - rho22_clean_med))

                    # Clean sanity + isolation conditions at RAW layer
                    clean_ok = (
                        (rho11_clean_med >= min_abs_main_clean_raw)
                        and (rho22_clean_med >= min_abs_main_clean_raw)
                        and (rho12_clean_med <= max_abs_xtalk_raw)
                        and (rho21_clean_med <= max_abs_xtalk_raw)
                    )
                    iso_ok = (drop_ratio <= max_drop_ratio) and (delta_rho22 <= max_delta_rho22)

                    point_pass = bool(clean_ok and iso_ok and (abs(float(msg12_corr)) <= float(target_abs_corr)))

                    results["grid"][key]["by_corrupt_frac"][str(float(frac))] = {"samples": samples, "aggregate": {
                        "rho11_clean_med_abs": float(rho11_clean_med),
                        "rho22_clean_med_abs": float(rho22_clean_med),
                        "rho12_clean_med_abs": float(rho12_clean_med),
                        "rho21_clean_med_abs": float(rho21_clean_med),
                        "rho11_mut_med_abs": float(rho11_mut_med),
                        "rho22_mut_med_abs": float(rho22_mut_med),
                        "drop_ratio": float(drop_ratio),
                        "delta_rho22": float(delta_rho22),
                        "clean_ok_raw": bool(clean_ok),
                        "iso_ok": bool(iso_ok),
                        "point_pass": bool(point_pass),
                    }}

                    if point_pass and best_star is None:
                        best_star = float(frac)

                # choose frac_star (minimal passing) else max frac
                if best_star is None:
                    frac_star = float(max(corrupt_fracs))
                else:
                    frac_star = float(best_star)
                    pass_points += 1

                results["grid"][key]["aggregate"] = {
                    "frac_star": float(frac_star),
                    "msg12_corr_after_warmup": float(msg12_corr),
                    "point_pass": bool(best_star is not None),
                }

                # For plot: use aggregate at frac_star
                agg_star = results["grid"][key]["by_corrupt_frac"][str(float(frac_star))]["aggregate"]
                drop_plot_rows.append((int(width), int(period), float(amp), float(frac_star), float(agg_star["drop_ratio"]), bool(best_star is not None)))

    # Summary + checks
    results["summary"] = {
        "msg12_corr_after_warmup": float(msg12_corr),
        "grid_total": int(total_grid),
        "pass_points": int(pass_points),
        "orthogonality_ok": bool(ok_ortho),
    }

    overall_ok = True
    overall_ok &= bool(ok_ortho)
    overall_ok &= (abs(float(msg12_corr)) <= float(target_abs_corr))
    overall_ok &= (pass_points > 0)

    results["checks"] = {
        "overall_pass": bool(overall_ok),
        "criteria": {
            "min_abs_main_clean_raw": float(min_abs_main_clean_raw),
            "max_abs_xtalk_raw": float(max_abs_xtalk_raw),
            "max_drop_ratio": float(max_drop_ratio),
            "max_delta_rho22": float(max_delta_rho22),
            "max_abs_msg12_corr": float(target_abs_corr),
            "chip1_vs_chip2_ortho_warn_thresh": float(ortho_warn),
            "require_some_pass_points": True,
        },
        "observed": {
            "pass_points": int(pass_points),
            "grid_total": int(total_grid),
            "msg12_corr_after_warmup": float(msg12_corr),
            "chip1_vs_chip2_inner_maxabs": float(chip_ortho["chip1_vs_chip2_inner_maxabs"]),
        },
    }

    # ----------------------------
    # plots
    # ----------------------------
    # Drop ratio vs amp (one curve per (w,p) using frac_star)
    plt.figure(figsize=(10, 4))
    labels_done = set()
    for (w, p, a, frac_star, drop, ok) in drop_plot_rows:
        pass  # we plot after grouping

    # group
    by_wp = {}
    for (w, p, a, frac_star, drop, ok) in drop_plot_rows:
        by_wp.setdefault((w, p), []).append((a, drop, frac_star, ok))
    for (w, p), rows in sorted(by_wp.items()):
        rows = sorted(rows, key=lambda r: r[0])
        xs = np.asarray([r[0] for r in rows], dtype=np.float64)
        ys = np.asarray([r[1] for r in rows], dtype=np.float64)
        lab = f"w={w} p={p}"
        plt.plot(xs, ys, marker="o", label=lab)
    plt.axhline(float(max_drop_ratio), linestyle="--")
    plt.xlabel("burst amp")
    plt.ylabel("drop_ratio = |rho11_mut|/|rho11_clean| (med abs)")
    plt.title("P10.1 Key Mutation: channel-1 collapse under bursts (RX-only mutation)")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_drop = OUT_DIR / "PAEV_P10_1_Mutation_DropRatio_vs_Amp.png"
    plt.savefig(p_png_drop, dpi=200)
    plt.close()

    # Pass map for mid-width (like P10)
    widths_sorted = sorted(set(int(w) for w in burst_widths))
    w_mid = int(widths_sorted[len(widths_sorted) // 2])
    P = np.asarray(sorted(set(int(pp) for pp in burst_periods)), dtype=np.int64)
    Aamps = np.asarray(sorted(set(float(aa) for aa in burst_amps)), dtype=np.float64)
    Z = np.zeros((Aamps.size, P.size), dtype=np.float64)

    for key, ent in results["grid"].items():
        w = int(ent["burst"]["width_steps"])
        if w != w_mid:
            continue
        p = int(ent["burst"]["period_steps"])
        a = float(ent["burst"]["amp"])
        ok = bool(ent["aggregate"]["point_pass"])
        i = int(np.where(np.isclose(Aamps, a))[0][0])
        j = int(np.where(P == p)[0][0])
        Z[i, j] = 1.0 if ok else 0.0

    plt.figure(figsize=(10, 4))
    plt.imshow(Z, aspect="auto", origin="lower",
               extent=[float(P.min()), float(P.max()), float(Aamps.min()), float(Aamps.max())])
    plt.colorbar(label="pass (1) / fail (0)")
    plt.xlabel("burst period (steps)")
    plt.ylabel("burst amp")
    plt.title(f"P10.1 Pass Map (key-mutation isolation) at width={w_mid} steps")
    plt.tight_layout()
    p_png_pass = OUT_DIR / "PAEV_P10_1_Mutation_PassMap.png"
    plt.savefig(p_png_pass, dpi=200)
    plt.close()

    out_json = OUT_DIR / "P10_1_mutation_multi_resilience.json"
    out_json.write_text(json.dumps(results, indent=2) + "\n")

    print("=== P10.1 — Resilience + Key Mutation (Multi) ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_png_drop}")
    print(f"✅ PNG  -> {p_png_pass}")
    print(f"RUN_ID  -> {run_id}")
    print(f"MODE    -> fast={bool(fast)} jobs={int(jobs_env)}")
    print(f"CHECKS  -> overall_pass={bool(overall_ok)} | orthogonality_ok={bool(ok_ortho)}")
    if not overall_ok:
        print("Observed:", results["checks"]["observed"])
        print("Criteria:", results["checks"]["criteria"])


if __name__ == "__main__":
    main()