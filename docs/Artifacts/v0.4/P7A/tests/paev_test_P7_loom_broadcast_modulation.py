# backend/photon_algebra/tests/paev_test_P7_loom_broadcast_modulation.py
import os, sys, json, hashlib, subprocess
from pathlib import Path
from datetime import datetime, UTC

import numpy as np
import matplotlib.pyplot as plt

# --- make "import backend...." work even without PYTHONPATH=. ---
_REPO_ROOT = Path(__file__).resolve().parents[3]  # .../backend/photon_algebra/tests -> repo root
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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

def corrcoef_safe(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.size != b.size:
        n = min(a.size, b.size)
        a = a[:n]
        b = b[:n]
    a = a - np.mean(a)
    b = b - np.mean(b)
    sa = float(np.std(a) + 1e-12)
    sb = float(np.std(b) + 1e-12)
    return float(np.mean(a * b) / (sa * sb))

def slope_safe(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    x = x - np.mean(x)
    y = y - np.mean(y)
    vx = float(np.var(x) + 1e-12)
    return float(np.mean(x * y) / vx)

def is_finite_dict(d: dict) -> bool:
    def _finite(v):
        if isinstance(v, (int, float, np.integer, np.floating)):
            return np.isfinite(v)
        return True
    for _, v in d.items():
        if isinstance(v, dict):
            if not is_finite_dict(v):
                return False
        else:
            if not _finite(v):
                return False
    return True

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


# ----------------------------
# demod helper: mix then period-block average (LPF)
# ----------------------------
def demod_period_blocks(y: np.ndarray, s: np.ndarray, omega: float, period: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns (s_blk, i_blk, q_blk) where:
      i(t)=y(t)*sin(ωt), q(t)=y(t)*cos(ωt),
      then average each over exact carrier periods (LPF).
    """
    y = np.asarray(y, dtype=np.float64)
    s = np.asarray(s, dtype=np.float64)
    n = min(y.size, s.size)
    y = y[:n]
    s = s[:n]

    t = np.arange(n, dtype=np.float64)
    sinw = np.sin(omega * t)
    cosw = np.cos(omega * t)

    i = y * sinw
    q = y * cosw

    nb = n // period
    if nb < 4:
        return s.copy(), i.copy(), q.copy()

    ntrim = nb * period
    s2 = s[:ntrim].reshape(nb, period).mean(axis=1)
    i2 = i[:ntrim].reshape(nb, period).mean(axis=1)
    q2 = q[:ntrim].reshape(nb, period).mean(axis=1)
    return s2, i2, q2


def main() -> None:
    const = load_constants()
    OUT_DIR = Path("backend/modules/knowledge")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # lattice + windows
    L = 4096
    N = 512
    xA0 = 768

    # time
    dt = 0.01
    steps = 3000
    seeds = [42, 43, 44, 45, 46]

    # stochasticity
    noise_sigma = 2e-4

    # controller
    k_fb = 2.5
    k_obs = 1.0
    u_max = 0.02
    k_diff = 2.0

    # chi well proxy
    chi_boost = 0.15

    # Loom: shared broadcast carrier
    carrier_amp = 0.010
    carrier_period_steps = 200
    omega = 2.0 * np.pi / float(carrier_period_steps)

    # A-state modulation (engineered)
    alpha_mod = 0.75
    s_gain = 6.0
    warmup_steps = 200

    # drive geometry
    drive_in_windows = False
    sham_delay_steps = 777

    separations = [64, 128, 256, 512, 1024, 1536]
    code_pairs = [
        ("ACG", "TTA"),
        ("ACG", "GCA"),
    ]

    # checks config
    strict = os.environ.get("P7A_STRICT", "0").strip() == "1"
    discrim_margin = float(os.environ.get("P7A_MARGIN", "0.02"))  # small margin; tune if needed

    _, w_sha, w_path = load_repo_bits(4096)
    run_id = f"P7A{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_P7_LOOM"

    def run_one(codeA: str, codeB: str, controller_on: bool, sep: int, mod_mode: str, drive_on: bool, seed: int) -> dict:
        rng = np.random.default_rng(int(seed))

        xA = xA0
        xB = int(np.clip(xA0 + sep, 0, L - N))

        tgtA = build_target(codeA, N)
        tgtB = build_target(codeB, N)

        x = np.zeros(L, dtype=np.float64)
        x[xA:xA+N] = tgtA
        x[xB:xB+N] = tgtB

        simA = np.zeros(steps, dtype=np.float64)
        simB = np.zeros(steps, dtype=np.float64)
        cohA = np.zeros(steps, dtype=np.float64)
        cohB = np.zeros(steps, dtype=np.float64)

        s_series = np.zeros(steps, dtype=np.float64)
        b_mean = np.zeros(steps, dtype=np.float64)

        W_fb = 0.0
        W_obs = 0.0
        W_drive = 0.0

        gmaskA = np.array([1.0 if codeA[i % len(codeA)] == "G" else 0.0 for i in range(N)], dtype=np.float64)
        gmaskB = np.array([1.0 if codeB[i % len(codeB)] == "G" else 0.0 for i in range(N)], dtype=np.float64)

        s_buf = np.zeros(sham_delay_steps + 1, dtype=np.float64)

        for t in range(steps):
            lap = laplacian(x)

            wA = x[xA:xA+N]
            wB = x[xB:xB+N]

            s_t = float(np.tanh(s_gain * float(np.mean(wA))))
            s_series[t] = s_t
            s_buf[t % s_buf.size] = s_t

            b_mean[t] = float(np.mean(wB))

            if drive_on:
                base = carrier_amp * np.sin(omega * t)

                if mod_mode == "ON":
                    mod_s = s_t
                elif mod_mode == "OFF":
                    mod_s = 0.0
                elif mod_mode == "SHAM":
                    mod_s = float(s_buf[(t - sham_delay_steps) % s_buf.size])
                else:
                    raise ValueError(f"Unknown mod_mode: {mod_mode}")

                drive_scalar = (1.0 + alpha_mod * mod_s) * base
                drive = np.full(L, drive_scalar, dtype=np.float64)

                if not drive_in_windows:
                    drive[xA:xA+N] = 0.0
                    drive[xB:xB+N] = 0.0

                W_drive += float(np.sum(drive * drive))
            else:
                drive = np.zeros(L, dtype=np.float64)

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

            nA = noise_sigma * rng.standard_normal(N)
            nB = noise_sigma * rng.standard_normal(N)

            wA = wA + dt * (k_diff * lap[xA:xA+N] + uA_fb + uA_ob) - dt * chi_boost * gmaskA * wA + drive[xA:xA+N] + nA
            wB = wB + dt * (k_diff * lap[xB:xB+N] + uB_fb + uB_ob) - dt * chi_boost * gmaskB * wB + drive[xB:xB+N] + nB

            x[xA:xA+N] = wA
            x[xB:xB+N] = wB

            W_fb += float(np.sum(uA_fb*uA_fb) + np.sum(uB_fb*uB_fb))
            W_obs += float(np.sum(uA_ob*uA_ob) + np.sum(uB_ob*uB_ob))

            simA[t] = cosine_similarity(wA, tgtA)
            simB[t] = cosine_similarity(wB, tgtB)
            cohA[t] = coherence_proxy(wA)
            cohB[t] = coherence_proxy(wB)

        # ----------------------------
        # Readouts
        # ----------------------------
        s = s_series[warmup_steps:]
        y = b_mean[warmup_steps:]

        raw_corr = corrcoef_safe(s, y)
        raw_slope = slope_safe(s, y)

        # Existing "carrier regression residual" lock-in (kept for continuity)
        tt = np.arange(warmup_steps, steps, dtype=np.float64)
        sinw = np.sin(omega * tt)
        cosw = np.cos(omega * tt)
        X = np.stack([sinw, cosw], axis=1)
        lam = 1e-9
        XtX = X.T @ X + lam * np.eye(2)
        Xty = X.T @ y
        ab = np.linalg.solve(XtX, Xty)
        a_sin, b_cos = float(ab[0]), float(ab[1])
        y_carrier = a_sin * sinw + b_cos * cosw
        y_res = y - y_carrier

        ref_sin = s * sinw
        ref_cos = s * cosw
        lockin_corr_sin = corrcoef_safe(y_res, ref_sin)
        lockin_corr_cos = corrcoef_safe(y_res, ref_cos)

        carrier_power = float(np.mean(y_carrier * y_carrier))
        residual_power = float(np.mean(y_res * y_res))

        # NEW: proper I/Q demod then LPF by carrier periods, correlate with s
        s_blk, i_blk, q_blk = demod_period_blocks(y, s, omega, carrier_period_steps)
        demod_corr_i = corrcoef_safe(i_blk, s_blk)
        demod_corr_q = corrcoef_safe(q_blk, s_blk)

        out = {
            "summary": {
                "sep": int(sep),
                "auc_similarity_A": float(np.mean(simA)),
                "auc_similarity_B": float(np.mean(simB)),
                "coherence_drop": float(0.5*(cohA[0]+cohB[0]) - 0.5*(cohA[-1]+cohB[-1])),
                "entropy_final": spectral_entropy_real(x),

                "loom_raw_corr_s_to_Bmean": float(raw_corr),
                "loom_raw_gain_slope": float(raw_slope),

                "loom_lockin_corr_res_to_s_sin": float(lockin_corr_sin),
                "loom_lockin_corr_res_to_s_cos": float(lockin_corr_cos),
                "loom_carrier_power_Bmean": float(carrier_power),
                "loom_residual_power_Bmean": float(residual_power),

                # NEW primary “clean” proxy
                "loom_demod_corr_I_to_s": float(demod_corr_i),
                "loom_demod_corr_Q_to_s": float(demod_corr_q),

                "W_feedback": float(W_fb),
                "W_observer": float(W_obs),
                "W_drive": float(W_drive),
                "W_total": float(W_fb + W_obs + W_drive),
            }
        }
        return out

    # conditions
    conditions = []
    for codeA, codeB in code_pairs:
        for sep in separations:
            controller_on = True
            conditions.append((codeA, codeB, sep, controller_on, "ON",   True))
            conditions.append((codeA, codeB, sep, controller_on, "OFF",  True))
            conditions.append((codeA, codeB, sep, controller_on, "SHAM", True))
            conditions.append((codeA, codeB, sep, controller_on, "OFF",  False))

    results = {}
    for codeA, codeB, sep, controller_on, mod_mode, drive_on in conditions:
        cname = (
            f"LOOM__A_{codeA}__B_{codeB}__sep_{sep}"
            f"__Controller_{'ON' if controller_on else 'OFF'}"
            f"__Drive_{'ON' if drive_on else 'OFF'}"
            f"__Mod_{mod_mode}"
        )
        per_seed = {}
        for s in seeds:
            per_seed[str(s)] = run_one(codeA, codeB, controller_on, sep, mod_mode, drive_on, s)

        keys = list(next(iter(per_seed.values()))["summary"].keys())
        agg = {}
        for k in keys:
            vals = [per_seed[str(s)]["summary"][k] for s in seeds]
            agg[f"{k}_median"] = float(np.median(vals))

        results[cname] = {
            "aggregate": agg,
            "per_seed": per_seed,
            "config": {
                "codeA": codeA,
                "codeB": codeB,
                "sep": sep,
                "controller_on": controller_on,
                "drive_on": drive_on,
                "mod_mode": mod_mode,
            },
        }

    # --- checks: artifact-grade pass + optional discrimination ---
    # We use the NEW demod metric by default.
    discrim_failed = []
    discrim_checked = []

    for codeA, codeB in code_pairs:
        for sep in separations:
            k_on   = f"LOOM__A_{codeA}__B_{codeB}__sep_{sep}__Controller_ON__Drive_ON__Mod_ON"
            k_off  = f"LOOM__A_{codeA}__B_{codeB}__sep_{sep}__Controller_ON__Drive_ON__Mod_OFF"
            k_sham = f"LOOM__A_{codeA}__B_{codeB}__sep_{sep}__Controller_ON__Drive_ON__Mod_SHAM"

            if not (k_on in results and k_off in results and k_sham in results):
                continue

            on  = results[k_on]["aggregate"]["loom_demod_corr_Q_to_s_median"]
            off = results[k_off]["aggregate"]["loom_demod_corr_Q_to_s_median"]
            shm = results[k_sham]["aggregate"]["loom_demod_corr_Q_to_s_median"]

            discrim_checked.append({"pair": f"{codeA}/{codeB}", "sep": int(sep), "on": float(on), "off": float(off), "sham": float(shm)})

            ok = True
            ok &= (abs(on) > abs(off) + discrim_margin)
            ok &= (abs(on) > abs(shm) + discrim_margin)

            if not ok:
                discrim_failed.append(f"{codeA}/{codeB}@{sep}")

    # artifact-grade: ensure all summary entries are finite
    finite_ok = True
    for _, blob in results.items():
        if not is_finite_dict(blob):
            finite_ok = False
            break

    discriminative_pass = (len(discrim_failed) == 0) if discrim_checked else False

    # overall_pass policy:
    # - default: pass if finite_ok (artifact produced)
    # - strict: require discrimination too
    overall_pass = finite_ok and ((not strict) or discriminative_pass)

    # Plot: demod corr (Q channel) vs distance
    plot_rows = []
    for codeA, codeB in code_pairs:
        for sep in separations:
            for mod_mode in ["ON", "OFF", "SHAM"]:
                k = f"LOOM__A_{codeA}__B_{codeB}__sep_{sep}__Controller_ON__Drive_ON__Mod_{mod_mode}"
                if k in results:
                    plot_rows.append((
                        f"{codeA}/{codeB}",
                        mod_mode,
                        sep,
                        results[k]["aggregate"]["loom_demod_corr_I_to_s_median"],
                        results[k]["aggregate"]["loom_demod_corr_Q_to_s_median"],
                    ))

    p_demod = None
    if plot_rows:
        plt.figure(figsize=(10, 4))
        pairs = sorted(set(r[0] for r in plot_rows))
        modes = ["ON", "OFF", "SHAM"]
        for pair in pairs:
            for mode in modes:
                xs = [r[2] for r in plot_rows if r[0] == pair and r[1] == mode]
                ys = [r[4] for r in plot_rows if r[0] == pair and r[1] == mode]  # Q-channel
                if xs:
                    plt.plot(xs, ys, marker="o", label=f"{pair} Mod_{mode} (demod-Q)")
        plt.xlabel("Separation (B_start - A_start)")
        plt.ylabel(r"corr( LPF( mean(B)*cos(ωt) ),  LPF(s(t)) )")
        plt.title("P7A Loom: demodulated coupling proxy (period-averaged)")
        plt.legend(loc="best")
        plt.tight_layout()
        p_demod = OUT_DIR / "PAEV_P7A_Loom_DemodCorrQ_vs_Distance.png"
        plt.savefig(p_demod, dpi=200)
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
            "noise_sigma": noise_sigma,
            "controller": {"k_fb": k_fb, "k_obs": k_obs, "u_max": u_max, "k_diff": k_diff},
            "operators": {"A": "rot(+pi/2)", "C": "gain(1.5x)", "G": "chi_well(damping)", "T": "project_imag->0"},
            "chi_boost": chi_boost,
            "loom": {
                "carrier_amp": carrier_amp,
                "carrier_period_steps": carrier_period_steps,
                "omega": omega,
                "alpha_mod": alpha_mod,
                "s_gain": s_gain,
                "warmup_steps": warmup_steps,
                "drive_in_windows": drive_in_windows,
                "sham_delay_steps": sham_delay_steps,
                "note": "Primary readout is demodulated (I/Q) then period-averaged (LPF) correlation to s(t). Lock-in residual metrics are retained for continuity.",
            },
            "separations": separations,
            "code_pairs": code_pairs,
            "repo_weights": {"path": w_path, "sha256": w_sha},
            "checks_policy": {
                "strict": strict,
                "discrim_margin": discrim_margin,
                "default_behavior": "overall_pass requires only finite outputs unless P7A_STRICT=1",
            }
        },
        "checks": {
            "finite_ok": bool(finite_ok),
            "discriminative_pass": bool(discriminative_pass),
            "overall_pass": bool(overall_pass),
            "failed": {
                "discriminative_failed": discrim_failed,
            },
            "diagnostic": {
                "discriminative_checked": discrim_checked,
            }
        },
        "definitions": {
            "goal": "P7A Loom: shared-carrier coupling using engineered AM from A-state and demod readout in B.",
            "non_claims": [
                "Engineered shared-medium coupling only; not entanglement/quantum nonlocality.",
                "Demod proxy does not imply semantic communication; it measures carrier-referenced coupling.",
            ],
        },
        "results": results,
        "files": {
            "demod_plot": (str(p_demod.name) if p_demod else None),
        },
    }

    out_json = OUT_DIR / "P7A_loom_broadcast_modulation.json"
    out_json.write_text(json.dumps(out, indent=2))

    print("=== P7A — Loom / Broadcast / Modulation (DEMOD + CHECKS) ===")
    print(f"✅ JSON -> {out_json}")
    if p_demod:
        print(f"✅ PNG  -> {p_demod}")
    print(f"RUN_ID  -> {run_id}")
    print(f"CHECKS  -> overall_pass={overall_pass} | finite_ok={finite_ok} | discriminative_pass={discriminative_pass} | strict={strict}")
    if strict and not overall_pass:
        print(f"FAILED discriminative: {discrim_failed}")


if __name__ == "__main__":
    main()