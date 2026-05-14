# backend/photon_algebra/tests/paev_test_P8_syntax_multiplexer.py
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
    if a.size != b.size:
        n = min(a.size, b.size)
        a = a[:n]
        b = b[:n]
    if a.size < 4:
        return 0.0
    a = a - np.mean(a)
    b = b - np.mean(b)
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
# deterministic PRN message (BLOCK-ALIGNED)
# ----------------------------
def prn_pm1(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=n, dtype=np.int64)
    return (2.0 * bits - 1.0).astype(np.float64)


# ----------------------------
# Walsh/Hadamard chips (EXACT ORTHOGONALITY PER BLOCK)
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
    base = H[r]  # length chips_per_block
    one_block = np.repeat(base, chip_spread).astype(np.float64)  # length despread_box
    reps = int(np.ceil(steps / one_block.size))
    return np.tile(one_block, reps)[:steps]


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ----------------------------
    # lattice / geometry
    # ----------------------------
    # IMPORTANT: L must be big enough so B and C never clip when we enforce non-overlap.
    L = 8192
    N = 512

    # Place A near center
    xA = (L // 2) - (N // 2)

    # We define "sep" as the GAP between windows (edge-to-edge),
    # so starts are xB = xA + N + sep, xC = xA - N - sep.
    separations = [64, 128, 256, 512, 1024, 1536]  # gap in lattice units

    # ----------------------------
    # time
    # ----------------------------
    dt = 0.01
    steps_raw = 16384
    seeds = [42, 43, 44, 45, 46]

    # controller (keep as in your earlier passing-style tests)
    controller_on = True
    k_fb = 2.5
    k_obs = 1.0
    u_max = 0.02
    k_diff = 2.0

    # chi well proxy (damping on G sites)
    chi_boost = 0.15

    # ----------------------------
    # spread-spectrum params (BLOCK-ALIGNED)
    # ----------------------------
    chip_spread      = 64
    despread_box     = 512
    chips_per_block  = despread_box // chip_spread  # 8
    msg_spread       = despread_box
    warmup_steps     = 2048
    warmup_steps     = (warmup_steps // despread_box) * despread_box
    if warmup_steps < despread_box:
        warmup_steps = despread_box

    # ----------------------------
    # drive: baseband DSSS (no carrier) for determinism
    # ----------------------------
    drive_amp  = 0.010
    alpha_mod  = 0.75

    # codes
    codeA = "ACG"
    codeB = "ACG"   # MATCH
    codeC = "TTA"   # MISMATCH

    # align steps to whole blocks
    steps = (steps_raw // despread_box) * despread_box
    if steps < despread_box * 8:
        raise ValueError("steps too small after alignment; increase steps_raw")
    nblocks = steps // despread_box
    warmup_blocks = warmup_steps // despread_box
    slb = slice(warmup_blocks, nblocks)

    # deterministic message seed from repo weights (NOT time/run_id)
    bits, w_sha, w_path, w_raw = load_repo_bits(4096)
    msg_seed = _seed_from_bytes(w_raw) ^ 0xA5A5_1234

    run_id = f"P8{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P8_MUX"

    # block-constant ±1
    msg_sym = prn_pm1(nblocks, msg_seed)
    msg = np.repeat(msg_sym, despread_box)[:steps].astype(np.float64)

    # Walsh rows
    walsh_row_AB = 1
    walsh_row_C  = 2
    walsh_row_SH = 3

    chipA  = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_AB)
    chipB  = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_AB)  # exact match
    chipC  = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_C)
    chipSH = make_walsh_chip(steps, chip_spread, chips_per_block, row=walsh_row_SH)

    assert msg.shape[0] == steps
    assert chipA.shape[0] == steps and chipB.shape[0] == steps and chipC.shape[0] == steps and chipSH.shape[0] == steps
    assert warmup_steps < steps

    meas_noise_sigma = 2e-4

    def simulate(sep_gap: int, tx_mode: str, seed: int) -> dict:
        rng = np.random.default_rng(int(seed))

        # NON-OVERLAPPING windows by construction
        xB = xA + N + int(sep_gap)
        xC = xA - N - int(sep_gap)

        # hard guard: no clipping, ever
        if not (0 <= xC <= L - N and 0 <= xB <= L - N):
            raise ValueError(f"Geometry out of bounds: sep_gap={sep_gap}, xA={xA}, xB={xB}, xC={xC}, L={L}, N={N}")

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

            # baseband DSSS drive
            if tx_mode == "MOD_ON":
                drive_scalar = drive_amp * (1.0 + alpha_mod * (msg[t] * chipA[t]))
            elif tx_mode == "MOD_SHAM":
                drive_scalar = drive_amp * (1.0 + alpha_mod * (msg[t] * chipSH[t]))
            else:
                drive_scalar = 0.0

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

            W_fb  += float(np.sum(uA_fb*uA_fb) + np.sum(uB_fb*uB_fb) + np.sum(uC_fb*uC_fb))
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

    # block-synchronous linear despread
    def demod_blocks_linear(time_series: np.ndarray, chip: np.ndarray) -> np.ndarray:
        y = np.asarray(time_series, dtype=np.float64)
        z = y * chip
        nb = steps // despread_box
        z = z[:nb * despread_box].reshape(nb, despread_box)
        return np.mean(z, axis=1)

    tx_modes = ["MOD_ON", "MOD_OFF", "MOD_SHAM"]
    results = {}
    for sep in separations:
        for tx_mode in tx_modes:
            cname = f"MUX__sep_{sep}__TX_{tx_mode}"
            results[cname] = {"per_seed": {}, "aggregate": {}, "config": {"sep_gap": sep, "tx_mode": tx_mode}}

    for sep in separations:
        for s in seeds:
            sim_off = simulate(sep_gap=sep, tx_mode="MOD_OFF", seed=s)
            sim_on  = simulate(sep_gap=sep, tx_mode="MOD_ON",  seed=s)
            sim_sh  = simulate(sep_gap=sep, tx_mode="MOD_SHAM", seed=s)

            # baseline subtraction in time domain
            dB_on = sim_on["meanB"] - sim_off["meanB"]
            dC_on = sim_on["meanC"] - sim_off["meanC"]
            dB_sh = sim_sh["meanB"] - sim_off["meanB"]
            dC_sh = sim_sh["meanC"] - sim_off["meanC"]

            yB_on = demod_blocks_linear(dB_on, chipB)
            yC_on = demod_blocks_linear(dC_on, chipC)
            yB_sh = demod_blocks_linear(dB_sh, chipB)
            yC_sh = demod_blocks_linear(dC_sh, chipC)

            mref = msg_sym.copy()

            rhoB_on = corr_safe(yB_on[slb], mref[slb])
            rhoC_on = corr_safe(yC_on[slb], mref[slb])
            rhoB_sh = corr_safe(yB_sh[slb], mref[slb])
            rhoC_sh = corr_safe(yC_sh[slb], mref[slb])

            d_on = float(abs(rhoB_on) - abs(rhoC_on))
            d_sh = float(abs(rhoB_sh) - abs(rhoC_sh))

            def put(mode: str, rhoB: float, rhoC: float, delta_abs: float, sim: dict):
                cname = f"MUX__sep_{sep}__TX_{mode}"
                results[cname]["per_seed"][str(s)] = {
                    "summary": {
                        "sep_gap": int(sep),
                        "tx_mode": mode,
                        "rho_B_matched": float(rhoB),
                        "rho_C_mismatch": float(rhoC),
                        "delta_absB_minus_absC": float(delta_abs),
                        "chip_corr_BA": float(corr_safe(chipB, chipA)),
                        "chip_corr_CA": float(corr_safe(chipC, chipA)),
                        "walsh": {
                            "chips_per_block": int(chips_per_block),
                            "row_AB": int(walsh_row_AB),
                            "row_C": int(walsh_row_C),
                            "row_SHAM": int(walsh_row_SH),
                        },
                        "W_feedback": float(sim["W_feedback"]),
                        "W_observer": float(sim["W_observer"]),
                        "W_drive": float(sim["W_drive"]),
                        "W_total": float(sim["W_total"]),
                    }
                }

            put("MOD_OFF", 0.0, 0.0, 0.0, sim_off)
            put("MOD_ON",  rhoB_on, rhoC_on, d_on, sim_on)
            put("MOD_SHAM", rhoB_sh, rhoC_sh, d_sh, sim_sh)

        # aggregates
        for mode in tx_modes:
            cname = f"MUX__sep_{sep}__TX_{mode}"
            keys = list(next(iter(results[cname]["per_seed"].values()))["summary"].keys())
            agg = {}
            for k in keys:
                vals = [results[cname]["per_seed"][str(ss)]["summary"][k] for ss in seeds]
                if all(isinstance(v, (int, float, np.integer, np.floating)) for v in vals):
                    agg[f"{k}_median"] = float(np.median(np.asarray(vals, dtype=np.float64)))
                else:
                    agg[k] = vals[0]
            results[cname]["aggregate"] = agg
            results[cname]["config"] = {"sep_gap": sep, "tx_mode": mode, "codeA": codeA, "codeB": codeB, "codeC": codeC}

    def _series(metric_key: str, tx_mode: str):
        xs, ys = [], []
        for sep in separations:
            cname = f"MUX__sep_{sep}__TX_{tx_mode}"
            xs.append(sep)
            ys.append(results[cname]["aggregate"][f"{metric_key}_median"])
        return xs, ys

    # plots
    plt.figure(figsize=(10, 4))
    for tx_mode in tx_modes:
        xs, ys = _series("delta_absB_minus_absC", tx_mode)
        plt.plot(xs, ys, marker="o", label=tx_mode)
    plt.xlabel("Gap between windows (B_start - (A_start+N) = (A_start - (C_start+N)))")
    plt.ylabel("median (|rho_B| - |rho_C|)")
    plt.title("P8 Syntax Multiplexer: delta (|matched B| minus |mismatch C|)")
    plt.legend(loc="best")
    plt.tight_layout()
    p_delta = OUT_DIR / "PAEV_P8_Multiplexer_Delta_vs_Distance.png"
    plt.savefig(p_delta, dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    for tx_mode in tx_modes:
        xs, ys = _series("rho_B_matched", tx_mode)
        plt.plot(xs, ys, marker="o", label=tx_mode)
    plt.xlabel("Gap")
    plt.ylabel("median rho_B_matched (block)")
    plt.title("P8: matched receiver B vs TX condition (block-despread, baseline-subtracted)")
    plt.legend(loc="best")
    plt.tight_layout()
    p_rhoB = OUT_DIR / "PAEV_P8_Multiplexer_RhoB_vs_Distance.png"
    plt.savefig(p_rhoB, dpi=200)
    plt.close()

    plt.figure(figsize=(10, 4))
    for tx_mode in tx_modes:
        xs, ys = _series("rho_C_mismatch", tx_mode)
        plt.plot(xs, ys, marker="o", label=tx_mode)
    plt.xlabel("Gap")
    plt.ylabel("median rho_C_mismatch (block)")
    plt.title("P8: mismatch receiver C vs TX condition (block-despread, baseline-subtracted)")
    plt.legend(loc="best")
    plt.tight_layout()
    p_rhoC = OUT_DIR / "PAEV_P8_Multiplexer_RhoC_vs_Distance.png"
    plt.savefig(p_rhoC, dpi=200)
    plt.close()

    # claim checks
    margin = 0.10
    max_abs_rhoC = 0.10

    failed = []
    for sep in separations:
        on  = results[f"MUX__sep_{sep}__TX_MOD_ON"]["aggregate"]
        shm = results[f"MUX__sep_{sep}__TX_MOD_SHAM"]["aggregate"]

        rhoB_on  = on["rho_B_matched_median"]
        rhoB_shm = shm["rho_B_matched_median"]
        rhoC_on  = on["rho_C_mismatch_median"]
        d_on     = on["delta_absB_minus_absC_median"]

        ok = True
        ok &= (abs(rhoB_on) > abs(rhoB_shm) + margin)
        ok &= (abs(rhoC_on) <= max_abs_rhoC)
        ok &= (d_on > margin)

        if not ok:
            failed.append(str(sep))

    overall_pass = (len(failed) == 0)

    out = {
        "timestamp": utc_ts(),
        "run_id": run_id,
        "git_rev": git_rev(),
        "constants": const,
        "params": {
            "lattice_size": L,
            "window_len": N,
            "dt": dt,
            "steps_raw": steps_raw,
            "steps_total": steps,
            "nblocks": nblocks,
            "seeds": seeds,
            "geometry": {
                "xA": xA,
                "separations_gap": separations,
                "layout": "B at xA+N+gap, C at xA-N-gap (non-overlapping by construction)",
            },
            "codes": {"A": codeA, "B_match": codeB, "C_mismatch": codeC},
            "controller": {"on": controller_on, "k_fb": k_fb, "k_obs": k_obs, "u_max": u_max, "k_diff": k_diff},
            "chi_boost": chi_boost,
            "mux": {
                "alpha_mod": alpha_mod,
                "drive": {"type": "baseband DSSS (no carrier)", "amp": drive_amp},
                "message": {"type": "block-aligned PRN (+1/-1)", "msg_spread": msg_spread, "seed": "repo-weights-derived"},
                "chip": {
                    "type": "Walsh/Hadamard (exact orthogonality per despread window)",
                    "chip_spread": chip_spread,
                    "despread_box": despread_box,
                    "chips_per_block": chips_per_block,
                    "walsh_row_AB": walsh_row_AB,
                    "walsh_row_C": walsh_row_C,
                    "walsh_row_SHAM": walsh_row_SH,
                },
                "demod": {
                    "method": "Linear: time-domain baseline subtraction, chip multiply, integrate-and-dump per block",
                    "warmup_steps": warmup_steps,
                    "warmup_blocks": warmup_blocks,
                    "meas_noise_sigma": meas_noise_sigma,
                },
            },
            "repo_weights": {"path": w_path, "sha256": w_sha},
            "claim_checks": {
                "margin": margin,
                "max_abs_rhoC": max_abs_rhoC,
                "require": [
                    "|rhoB_on| > |rhoB_sham| + margin",
                    "|rhoC_on| <= max_abs_rhoC",
                    "delta_on > margin",
                ],
            },
        },
        "checks": {"overall_pass": bool(overall_pass), "failed_seps": failed},
        "results": results,
        "files": {"delta_plot": str(p_delta.name), "rhoB_plot": str(p_rhoB.name), "rhoC_plot": str(p_rhoC.name)},
        "definitions": {
            "goal": "Selective listening in a shared broadcast medium: matched receiver B decodes injected message; mismatch receiver C does not.",
            "non_claims": ["This is engineered comms (spread-spectrum + matched filtering), not quantum effects or biological translation."],
        },
    }

    out_json = OUT_DIR / "P8_syntax_multiplexer.json"
    out_json.write_text(json.dumps(out, indent=2))

    print("=== P8 — Syntax Multiplexer (Selective Listening) ===")
    print(f"✅ JSON -> {out_json}")
    print(f"✅ PNG  -> {p_delta}")
    print(f"✅ PNG  -> {p_rhoB}")
    print(f"✅ PNG  -> {p_rhoC}")
    print(f"RUN_ID  -> {run_id}")
    print(f"CHECKS  -> overall_pass={overall_pass}")
    if not overall_pass:
        print(f"FAILED seps: {failed}")


if __name__ == "__main__":
    main()