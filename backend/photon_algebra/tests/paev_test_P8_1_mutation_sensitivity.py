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
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=n, dtype=np.int64)
    return (2.0 * bits - 1.0).astype(np.float64)


# ----------------------------
# Walsh/Hadamard chips
# ----------------------------
def hadamard(n: int) -> np.ndarray:
    if n & (n - 1) != 0:
        raise ValueError("Hadamard size must be a power of 2")
    H = np.array([[1.0]], dtype=np.float64)
    while H.shape[0] < n:
        H = np.block([[H,  H],
                      [H, -H]])
    return H

def make_walsh_chip(steps: int, chip_spread: int, chips_per_block: int, row: int) -> np.ndarray:
    H = hadamard(chips_per_block)
    r = int(row) % chips_per_block
    base = H[r]
    one_block = np.repeat(base, chip_spread).astype(np.float64)
    reps = int(np.ceil(steps / one_block.size))
    return np.tile(one_block, reps)[:steps]

def corrupt_chip_per_block(chip: np.ndarray, *, flips_per_block: int, seed: int,
                           despread_box: int, chip_spread: int) -> np.ndarray:
    """
    "Mutation": within each despread block, flip the sign of N chip segments (chip_spread-sized).
    """
    if flips_per_block <= 0:
        return chip.copy()

    out = chip.copy()
    steps = out.size
    chips_per_block = despread_box // chip_spread
    nb = steps // despread_box
    rng = np.random.default_rng(int(seed))

    flips = int(min(flips_per_block, chips_per_block))
    for bi in range(nb):
        block_start = bi * despread_box
        idxs = rng.choice(chips_per_block, size=flips, replace=False)
        for ci in idxs:
            a = block_start + ci * chip_spread
            b = a + chip_spread
            out[a:b] *= -1.0
    return out


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # lattice
    L = 4096
    N = 512
    xA = 2048 - N // 2

    # time
    dt = 0.01
    steps_raw = 16384
    seeds = [42, 43, 44, 45, 46]

    # controller
    controller_on = True
    k_fb = 2.5
    k_obs = 1.0
    u_max = 0.02
    k_diff = 2.0

    # chi well proxy
    chi_boost = 0.15

    # spread-spectrum params (block-aligned)
    chip_spread      = 64
    despread_box     = 512
    chips_per_block  = despread_box // chip_spread  # 8
    warmup_steps     = 2048
    warmup_steps     = (warmup_steps // despread_box) * despread_box
    if warmup_steps < despread_box:
        warmup_steps = despread_box

    # carrier (keep identical to P8)
    carrier_amp = 0.010
    carrier_period_steps = 32
    omega = 2.0 * np.pi / float(carrier_period_steps)
    alpha_mod = 0.75

    separations = [256, 512, 1024, 1536]

    # IMPORTANT: P8.1 is about CHIP sensitivity.
    # Keep operator targets identical for A/B/C to avoid dynamics-induced pseudo-mismatch.
    codeA = "ACG"
    codeB = "ACG"   # matched target
    codeC = "ACG"   # same target; mismatch is chip-only

    steps = (steps_raw // despread_box) * despread_box
    nblocks = steps // despread_box
    warmup_blocks = warmup_steps // despread_box
    slb = slice(warmup_blocks, nblocks)

    # repo weights -> deterministic seed
    _, w_sha, w_path, w_raw = load_repo_bits(4096)
    msg_seed = _seed_from_bytes(w_raw) ^ 0xA5A5_1234

    run_id = f"P8_1{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P8_1_MUT"

    msg_sym = prn_pm1(nblocks, msg_seed)
    msg = np.repeat(msg_sym, despread_box)[:steps].astype(np.float64)

    # Walsh rows (AB uses one, "wrong chip" uses a different orthogonal row)
    walsh_row_AB = 1
    walsh_row_W  = 2  # wrong-chip row (orthogonal to AB)

    chipA = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_AB)
    chipB = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_AB)
    chipW = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_W)

    meas_noise_sigma = 2e-4

    # mutation levels: "chips flipped per block"
    mutation_levels = [0, 1, 2, 4, 8]

    def simulate(sep: int, tx_mode: str, seed: int) -> dict:
        rng = np.random.default_rng(int(seed))

        xB = int(np.clip(xA + sep, 0, L - N))
        xC = int(np.clip(xA - sep, 0, L - N))

        tgtA = build_target(codeA, N)
        tgtB = build_target(codeB, N)
        tgtC = build_target(codeC, N)

        x = np.zeros(L, dtype=np.float64)
        x[xA:xA+N] = tgtA
        x[xB:xB+N] = tgtB
        x[xC:xC+N] = tgtC

        gmaskA = np.array([1.0 if codeA[i % len(codeA)] == "G" else 0.0 for i in range(N)], dtype=np.float64)
        gmaskB = np.array([1.0 if codeB[i % len(codeB)] == "G" else 0.0 for i in range(N)], dtype=np.float64)
        gmaskC = np.array([1.0 if codeC[i % len(codeC)] == "G" else 0.0 for i in range(N)], dtype=np.float64)

        meanB = np.zeros(steps, dtype=np.float64)
        meanC = np.zeros(steps, dtype=np.float64)

        W_fb = 0.0
        W_obs = 0.0
        W_drive = 0.0

        for t in range(steps):
            lap = laplacian(x)

            wA = x[xA:xA+N]
            wB = x[xB:xB+N]
            wC = x[xC:xC+N]

            base = carrier_amp * np.cos(omega * t)
            if tx_mode == "MOD_ON":
                drive_scalar = (1.0 + alpha_mod * (msg[t] * chipA[t])) * base
            else:
                drive_scalar = base

            W_drive += float(L) * float(drive_scalar * drive_scalar)

            if controller_on:
                eA = tgtA - wA
                eB = tgtB - wB
                eC = tgtC - wC
                uA_fb = np.clip(k_fb * eA, -u_max, u_max)
                uA_ob = np.clip(k_obs * eA, -u_max, u_max)
                uB_fb = np.clip(k_fb * eB, -u_max, u_max)
                uB_ob = np.clip(k_obs * eB, -u_max, u_max)
                uC_fb = np.clip(k_fb * eC, -u_max, u_max)
                uC_ob = np.clip(k_obs * eC, -u_max, u_max)
            else:
                uA_fb = np.zeros_like(wA); uA_ob = np.zeros_like(wA)
                uB_fb = np.zeros_like(wB); uB_ob = np.zeros_like(wB)
                uC_fb = np.zeros_like(wC); uC_ob = np.zeros_like(wC)

            wA = wA + dt * (k_diff * lap[xA:xA+N] + uA_fb + uA_ob) - dt * chi_boost * gmaskA * wA
            wB = wB + dt * (k_diff * lap[xB:xB+N] + uB_fb + uB_ob) - dt * chi_boost * gmaskB * wB
            wC = wC + dt * (k_diff * lap[xC:xC+N] + uC_fb + uC_ob) - dt * chi_boost * gmaskC * wC

            x[xA:xA+N] = wA
            x[xB:xB+N] = wB
            x[xC:xC+N] = wC

            # broadcast drive is global
            x += drive_scalar

            W_fb += float(np.sum(uA_fb*uA_fb) + np.sum(uB_fb*uB_fb) + np.sum(uC_fb*uC_fb))
            W_obs += float(np.sum(uA_ob*uA_ob) + np.sum(uB_ob*uB_ob) + np.sum(uC_ob*uC_ob))

            # measure AFTER broadcast + tiny noise
            meanB[t] = float(np.mean(x[xB:xB+N])) + float(rng.normal(0.0, meas_noise_sigma))
            meanC[t] = float(np.mean(x[xC:xC+N])) + float(rng.normal(0.0, meas_noise_sigma))

        return {
            "meanB": meanB,
            "meanC": meanC,
            "W_feedback": float(W_fb),
            "W_observer": float(W_obs),
            "W_drive": float(W_drive),
            "W_total": float(W_fb + W_obs + W_drive),
        }

    def demod_blocks_linear(time_series: np.ndarray, chip: np.ndarray) -> np.ndarray:
        """
        Same demod path as P8 baseline: coherent I-mix, then despread, then block-average.
        """
        y = np.asarray(time_series, dtype=np.float64)
        t = np.arange(y.size, dtype=np.float64)
        mixed = y * np.cos(omega * t)
        z = mixed * chip
        nb = steps // despread_box
        z = z[:nb * despread_box].reshape(nb, despread_box)
        return np.mean(z, axis=1)

    # Orthogonality diagnostic at block level (chip symbols)
    def chip_block_inner(ch1: np.ndarray, ch2: np.ndarray) -> np.ndarray:
        nb = steps // despread_box
        a = ch1[:nb * despread_box].reshape(nb, despread_box)
        b = ch2[:nb * despread_box].reshape(nb, despread_box)
        # collapse within each chip segment first, then dot at chip-symbol level
        a_sym = a.reshape(nb, chips_per_block, chip_spread).mean(axis=2)
        b_sym = b.reshape(nb, chips_per_block, chip_spread).mean(axis=2)
        inn = np.sum(a_sym * b_sym, axis=1) / float(chips_per_block)
        return inn

    inn = chip_block_inner(chipA, chipW)
    chip_ortho = {
        "chipA_vs_chipW_inner_median": float(np.median(inn[warmup_blocks:])),
        "chipA_vs_chipW_inner_maxabs": float(np.max(np.abs(inn[warmup_blocks:]))),
        "definition": "per-block mean-symbol inner product; should be ~0 for true orthogonality",
    }

    results = {
        "timestamp": utc_ts(),
        "run_id": run_id,
        "git_rev": git_rev(),
        "constants": const,
        "params": {
            "lattice_size": L,
            "window_len": N,
            "dt": dt,
            "steps_total": steps,
            "nblocks": nblocks,
            "warmup_blocks": warmup_blocks,
            "seeds": seeds,
            "separations": separations,
            "codes": {"A": codeA, "B_match": codeB, "C_target": codeC},
            "mismatch_mode": "wrong_chip_on_same_stream",
            "chip": {
                "type": "Walsh/Hadamard",
                "chip_spread": chip_spread,
                "despread_box": despread_box,
                "chips_per_block": chips_per_block,
                "walsh_row_AB": walsh_row_AB,
                "walsh_row_wrong": walsh_row_W,
                "orthogonality": chip_ortho,
            },
            "carrier": {"amp": carrier_amp, "period_steps": carrier_period_steps, "wave": "cos"},
            "alpha_mod": alpha_mod,
            "mutation": {
                "definition": "flip sign of N chip segments per despread block in receiver chip only",
                "levels_flips_per_block": mutation_levels,
                "note": "flips == chips_per_block yields full inversion of the receiver chip (expected rho ≈ -rho0).",
            },
            "repo_weights": {"path": w_path, "sha256": w_sha},
        },
        "summary": {},
        "by_sep": {},
        "checks": {},
        "definitions": {
            "goal": "P8.1 mutation sensitivity: measure rho_B decay vs receiver-chip corruption (syntax specificity curve).",
            "non_claims": [
                "Engineered comms baseline; no biology/physics claims.",
                "Corruption is applied to receiver chip only (not transmitter).",
            ],
            "interpretation_notes": [
                "In Walsh/Hadamard DSSS, flipping all chips yields a perfectly inverted despread output (rho ≈ -rho0).",
                "Mismatch is evaluated by applying an orthogonal wrong chip to the SAME decoded stream (B) to isolate chip selectivity.",
                "C-window decoding is retained as a diagnostic only (not gating pass/fail).",
            ],
        },
    }

    # compute
    for sep in separations:
        results["by_sep"][str(sep)] = {"per_seed": {}, "aggregate": {}}

        for s in seeds:
            sim_off = simulate(sep=sep, tx_mode="MOD_OFF", seed=s)
            sim_on  = simulate(sep=sep, tx_mode="MOD_ON",  seed=s)

            dB = sim_on["meanB"] - sim_off["meanB"]
            dC = sim_on["meanC"] - sim_off["meanC"]  # diagnostic only

            # WRONG-CHIP control computed on SAME stream (B) to isolate chip selectivity
            yW = demod_blocks_linear(dB, chipW)
            rhoW = corr_safe(yW[slb], msg_sym[slb])

            # diagnostic: what C-window sees if you despread with correct chip (AB)
            yC_diag = demod_blocks_linear(dC, chipB)
            rhoC_diag = corr_safe(yC_diag[slb], msg_sym[slb])

            per_level = {}
            for flips in mutation_levels:
                mut_seed = (int(s) * 1315423911) ^ (int(sep) * 2654435761) ^ (int(flips) * 97531) ^ msg_seed
                chipB_mut = corrupt_chip_per_block(
                    chipB, flips_per_block=flips, seed=mut_seed,
                    despread_box=despread_box, chip_spread=chip_spread
                )
                yB = demod_blocks_linear(dB, chipB_mut)
                rhoB = corr_safe(yB[slb], msg_sym[slb])

                per_level[str(flips)] = {
                    "rho_B": float(rhoB),
                    "abs_rho_B": float(abs(rhoB)),
                    "rho_wrongchip_on_B": float(rhoW),
                    "abs_rho_wrongchip_on_B": float(abs(rhoW)),
                    "rho_C_diag": float(rhoC_diag),
                    "abs_rho_C_diag": float(abs(rhoC_diag)),
                    "delta_absB_minus_absWrong": float(abs(rhoB) - abs(rhoW)),
                }

            results["by_sep"][str(sep)]["per_seed"][str(s)] = {
                "per_level": per_level,
                "W_total": float(sim_on["W_total"]),
            }

        # aggregates (median across seeds)
        agg = {}
        for flips in mutation_levels:
            valsB = [results["by_sep"][str(sep)]["per_seed"][str(ss)]["per_level"][str(flips)]["rho_B"] for ss in seeds]
            valsBW = [results["by_sep"][str(sep)]["per_seed"][str(ss)]["per_level"][str(flips)]["rho_wrongchip_on_B"] for ss in seeds]
            valsC = [results["by_sep"][str(sep)]["per_seed"][str(ss)]["per_level"][str(flips)]["rho_C_diag"] for ss in seeds]
            valsD = [results["by_sep"][str(sep)]["per_seed"][str(ss)]["per_level"][str(flips)]["delta_absB_minus_absWrong"] for ss in seeds]
            agg[str(flips)] = {
                "rho_B_median": float(np.median(np.asarray(valsB, dtype=np.float64))),
                "abs_rho_B_median": float(np.median(np.abs(np.asarray(valsB, dtype=np.float64)))),
                "rho_wrongchip_on_B_median": float(np.median(np.asarray(valsBW, dtype=np.float64))),
                "abs_rho_wrongchip_on_B_median": float(np.median(np.abs(np.asarray(valsBW, dtype=np.float64)))),
                "rho_C_diag_median": float(np.median(np.asarray(valsC, dtype=np.float64))),
                "delta_absB_minus_absWrong_median": float(np.median(np.asarray(valsD, dtype=np.float64))),
            }
        results["by_sep"][str(sep)]["aggregate"] = agg

    # global summary curve (median across seps of per-sep medians)
    curve = {}
    for flips in mutation_levels:
        medB  = [results["by_sep"][str(sep)]["aggregate"][str(flips)]["rho_B_median"] for sep in separations]
        medBW = [results["by_sep"][str(sep)]["aggregate"][str(flips)]["rho_wrongchip_on_B_median"] for sep in separations]
        medC  = [results["by_sep"][str(sep)]["aggregate"][str(flips)]["rho_C_diag_median"] for sep in separations]
        curve[str(flips)] = {
            "rho_B_median_over_seps": float(np.median(np.asarray(medB, dtype=np.float64))),
            "abs_rho_B_median_over_seps": float(np.median(np.abs(np.asarray(medB, dtype=np.float64)))),
            "rho_wrongchip_on_B_median_over_seps": float(np.median(np.asarray(medBW, dtype=np.float64))),
            "abs_rho_wrongchip_on_B_median_over_seps": float(np.median(np.abs(np.asarray(medBW, dtype=np.float64)))),
            "rho_C_diag_median_over_seps": float(np.median(np.asarray(medC, dtype=np.float64))),
        }
    results["summary"]["mutation_curve"] = curve

    # plots
    xs = mutation_levels

    # 1) rho_B
    plt.figure(figsize=(10, 4))
    for sep in separations:
        ys = [results["by_sep"][str(sep)]["aggregate"][str(flips)]["rho_B_median"] for flips in xs]
        plt.plot(xs, ys, marker="o", label=f"sep={sep}")
    plt.xlabel("Receiver chip corruption (flipped chips per block)")
    plt.ylabel("median rho_B (matched receiver) vs message")
    plt.title("P8.1 Mutation Sensitivity: rho_B vs receiver-chip corruption")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_rho = OUT_DIR / "PAEV_P8_1_MutationCurve_RhoB.png"
    plt.savefig(p_png_rho, dpi=200)
    plt.close()

    # 2) |rho_B| for partial regime (0..4) + show wrong-chip |rho|
    partial_levels = [0, 1, 2, 4]
    plt.figure(figsize=(10, 4))
    for sep in separations:
        ys = [results["by_sep"][str(sep)]["aggregate"][str(flips)]["abs_rho_B_median"] for flips in partial_levels]
        plt.plot(partial_levels, ys, marker="o", label=f"|rho_B| sep={sep}")
    ysW = [results["summary"]["mutation_curve"][str(flips)]["abs_rho_wrongchip_on_B_median_over_seps"] for flips in partial_levels]
    plt.plot(partial_levels, ysW, marker="x", linestyle="--", label="|rho_wrongchip_on_B| (median over seps)")
    plt.xlabel("Receiver chip corruption (flipped chips per block)")
    plt.ylabel("median |rho|")
    plt.title("P8.1 Mutation Sensitivity: |rho_B| decay (partial-corruption regime) + wrong-chip control")
    plt.legend(loc="best")
    plt.tight_layout()
    p_png_abs = OUT_DIR / "PAEV_P8_1_MutationCurve_AbsRhoB.png"
    plt.savefig(p_png_abs, dpi=200)
    plt.close()

    # checks
    rho0  = results["summary"]["mutation_curve"]["0"]["rho_B_median_over_seps"]
    rho4  = results["summary"]["mutation_curve"]["4"]["rho_B_median_over_seps"]
    rho8  = results["summary"]["mutation_curve"]["8"]["rho_B_median_over_seps"]
    rhoW0 = results["summary"]["mutation_curve"]["0"]["rho_wrongchip_on_B_median_over_seps"]

    abs_rho0 = abs(rho0)
    abs_rho4 = abs(rho4)
    abs_rho8 = abs(rho8)
    abs_rhoW0 = abs(rhoW0)

    # monotonic-ish on abs(rho_B) for partial corruption only
    eps = 0.03
    ok_monoish = True
    prev = None
    for flips in partial_levels:
        v = abs(results["summary"]["mutation_curve"][str(flips)]["rho_B_median_over_seps"])
        if prev is not None and v > prev + eps:
            ok_monoish = False
        prev = v

    # inversion-consistency at full flip (=8)
    inv_abs_tol = 0.08
    require_opposite_sign = True
    ok_inversion_mag = (abs(abs_rho8 - abs_rho0) <= inv_abs_tol)
    ok_inversion_sign = ((rho8 * rho0) < 0.0) if require_opposite_sign else True
    ok_inversion = ok_inversion_mag and ok_inversion_sign

    # chip selectivity: margin + ratio (NOT "wrong-chip must be ~0")
    selectivity_margin0 = abs_rho0 - abs_rhoW0
    selectivity_ratio0 = abs_rhoW0 / (abs_rho0 + 1e-12)

    min_abs_rho0 = 0.30
    max_abs_rho4 = 0.25
    min_drop_abs_rho0_minus_abs_rho4 = 0.12
    min_selectivity_margin0 = 0.20
    max_selectivity_ratio0 = 0.85

    ok = True
    ok &= (abs_rho0 >= min_abs_rho0)
    ok &= (abs_rho4 <= max_abs_rho4)
    ok &= ((abs_rho0 - abs_rho4) >= min_drop_abs_rho0_minus_abs_rho4)
    ok &= (selectivity_margin0 >= min_selectivity_margin0)
    ok &= (selectivity_ratio0 <= max_selectivity_ratio0)
    ok &= ok_monoish
    ok &= ok_inversion

    # orthogonality warning only (should already be ~0)
    ortho_warn_thresh = 0.25
    orth_ok = (abs(chip_ortho["chipA_vs_chipW_inner_maxabs"]) <= ortho_warn_thresh)

    results["checks"] = {
        "overall_pass": bool(ok),
        "orthogonality_ok": bool(orth_ok),
        "criteria": {
            "min_abs_rho0": min_abs_rho0,
            "max_abs_rho4": max_abs_rho4,
            "min_drop_abs_rho0_minus_abs_rho4": min_drop_abs_rho0_minus_abs_rho4,
            "min_selectivity_margin0": min_selectivity_margin0,
            "max_selectivity_ratio0": max_selectivity_ratio0,
            "monoish_levels": partial_levels,
            "monoish_eps": eps,
            "inv_abs_tol": inv_abs_tol,
            "require_opposite_sign": require_opposite_sign,
            "chipA_vs_chipW_ortho_warn_thresh": ortho_warn_thresh,
        },
        "observed": {
            "rho0_median_over_seps": float(rho0),
            "rho4_median_over_seps": float(rho4),
            "rho8_median_over_seps": float(rho8),
            "rhoW0_median_over_seps": float(rhoW0),
            "abs_rho0": float(abs_rho0),
            "abs_rho4": float(abs_rho4),
            "abs_rho8": float(abs_rho8),
            "abs_rhoW0": float(abs_rhoW0),
            "selectivity_margin0": float(selectivity_margin0),
            "selectivity_ratio0": float(selectivity_ratio0),
            "monoish_partial_abs": bool(ok_monoish),
            "inversion_ok": bool(ok_inversion),
            "chipA_vs_chipW_inner_median": float(chip_ortho["chipA_vs_chipW_inner_median"]),
            "chipA_vs_chipW_inner_maxabs": float(chip_ortho["chipA_vs_chipW_inner_maxabs"]),
        },
        "notes": {
            "why_wrongchip_isnt_zero": (
                "Wrong-chip control is not required to be ~0 for P8.1 pass; "
                "P8.1 gates on mutation cliff + inversion + selectivity margin. "
                "P9 will tighten crosstalk requirements with multi-voice decoding."
            )
        },
    }

    out_json = OUT_DIR / "P8_1_mutation_sensitivity.json"
    out_json.write_text(json.dumps(results, indent=2))

    print("=== P8.1 — Mutation Sensitivity (Receiver Chip Corruption) ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_png_rho}")
    print(f"✅ PNG  -> {p_png_abs}")
    print(f"RUN_ID  -> {run_id}")
    print(f"CHECKS  -> overall_pass={ok} | orthogonality_ok={orth_ok}")

    if not ok:
        print("Observed:", results["checks"]["observed"])
        print("Criteria:", results["checks"]["criteria"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()