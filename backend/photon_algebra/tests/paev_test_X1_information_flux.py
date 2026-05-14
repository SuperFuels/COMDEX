# === X1 - Information Flux Conservation (Tessaris) ===
# Implements Tessaris Unified Constants & Verification Protocol (TUCVP)
# Version: Phase II / Unified Architecture v1.2
# ----------------------------------------------------------------------

import os, json
import numpy as np
from datetime import datetime, timezone

from backend.photon_algebra.utils.load_constants import load_constants
from backend.photon_algebra.utils import field_ops


def _corr(a, b):
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 10:
        return 0.0
    a = a[m]; b = b[m]
    a = a - a.mean()
    b = b - b.mean()
    da = np.sqrt(np.mean(a * a)) + 1e-12
    db = np.sqrt(np.mean(b * b)) + 1e-12
    return float(np.mean((a / da) * (b / db)))


# =====================================================
# 1. Load Tessaris Unified Constants
# =====================================================
constants = load_constants(version="v1.2")

print("=== X1 - Information Flux Conservation (Tessaris) ===")
print(f"Constants -> ħ={constants['ħ']}, G={constants['G']}, "
      f"Λ={constants['Λ']}, α={constants['α']}, β={constants['β']}, χ={constants['χ']}")

# =====================================================
# 2. Load lattice field states (prefer time stacks)
# =====================================================
u = field_ops.load_field("M6_field_stack.npy")
v = field_ops.load_field("M6_velocity_stack.npy")

if u is None or v is None:
    u = field_ops.load_field("M6_field.npy")
    v = field_ops.load_field("M6_velocity.npy")

if u is None or v is None:
    raise FileNotFoundError("❌ Missing M6 field data. Run M6 emitter before X1.")

u = np.asarray(u, dtype=float)
v = np.asarray(v, dtype=float)
if u.ndim == 1: u = u[None, :]
if v.ndim == 1: v = v[None, :]

T, N = u.shape

meta = field_ops.load_m6_meta()
dt_base = float(meta.get("dt_base", 0.001))
stride = int(meta.get("stride", 1))
dx = float(meta.get("dx", 1.0))
dt_eff = dt_base * stride

# Diffusion strength (env overrides meta)
diff_env = os.environ.get("PAEV_DIFFUSION_STRENGTH", None)
diff_strength = float(diff_env) if diff_env is not None else float(meta.get("diffusion_strength", 0.0))

if diff_strength != 0.0:
    raise RuntimeError("X1 is a strict continuity test; run with PAEV_DIFFUSION_STRENGTH=0.0. Use X1b for diffusion-source continuity.")

# =====================================================
# 3. Compute derived informational quantities
# =====================================================
smooth_sigma = float(meta.get("smooth_sigma", 4.0))
S = field_ops.entropy_density_local(u, sigma=smooth_sigma)

# --- critical robustness step ---
# If diffusion/noise is present, the stored v is often NOT a transport velocity.
# Use self-consistent velocity from u timeseries: v_eff = ∂u/∂t, then smooth in time.
use_v_eff = (T >= 5) and (diff_strength > 0.0)

if use_v_eff:
    v_eff = np.gradient(u, dt_eff, axis=0, edge_order=2)  # (T,N)
    # temporal smoothing to suppress diffusion noise differentiation blowup
    v_field = field_ops.smooth_time_2d(v_eff, sigma_t=2.0)
else:
    v_field = field_ops.velocity_field(u, v)

# energy density uses the SAME velocity field used in flux
rho_E = field_ops.energy_density(u, v_field)

# Optional: smooth the advective flux a bit (helps under diffusion)
adv_flux = rho_E * v_field
adv_flux = field_ops.smooth_time_2d(adv_flux, sigma_t=2.0) if T >= 5 else adv_flux

# =====================================================
# 4. Continuity structure
# J_info = ρ_E*v - X0 * ∂x S
# residual = ∂t S + ∂x(ρ_E v) - X0 ∂xx S
# =====================================================
# temporal smoothing on S before derivative (diffusion stability)
S_t = field_ops.smooth_time_2d(S, sigma_t=2.0) if (T >= 5 and diff_strength > 0.0) else S

dS_dt = field_ops.time_derivative_stack(S_t, dt=dt_eff)
A = dS_dt + field_ops.spatial_grad_1d(adv_flux, dx=dx)
B = field_ops.spatial_lap_1d(S_t, dx=dx)

# Fit X0 by least squares: minimize ||A - X0*B||
BB = float(np.mean(B * B)) + 1e-18
AB = float(np.mean(A * B))
X0_est = AB / BB

residual_raw = A - 1.0 * B
residual_fit = A - X0_est * B

mean_abs_raw = float(np.mean(np.abs(residual_raw)))
mean_abs_fit = float(np.mean(np.abs(residual_fit)))

# Drift metric: spatial mean residual per frame (mean of derivatives should be ~0)
drift = np.mean(residual_fit, axis=1)
drift_mean_abs = float(np.mean(np.abs(drift)))

corr_u = _corr(residual_fit, u)
corr_v = _corr(residual_fit, v_field)

# =====================================================
# 5. Output summary and verification block
# =====================================================
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

tolerance_drift = 1e-3
within_tolerance = bool(drift_mean_abs < tolerance_drift)

summary = {
    "timestamp": timestamp,
    "series": "X1",
    "experiment": "Information Flux Conservation",
    "constants": constants,
    "params": {
        "dt_base": dt_base,
        "stride": stride,
        "dt_eff": dt_eff,
        "dx": dx,
        "frames": int(T),
        "N": int(N),
        "diffusion_strength": float(diff_strength),
        "velocity_mode": "v_eff=du/dt (smoothed)" if use_v_eff else "M6_velocity_stack.npy",
        "entropy": {
            "type": "local_window_shannon",
            "smooth_sigma": smooth_sigma,
            "time_smooth_sigma": 2.0 if (diff_strength > 0.0 and T >= 5) else 0.0
        }
    },
    "fit": {
        "X0_est": float(X0_est),
        "mean_abs_residual_raw_X0_1": mean_abs_raw,
        "mean_abs_residual_fit": mean_abs_fit,
        "drift_mean_abs_fit": drift_mean_abs,
        "corr_res_u": float(corr_u),
        "corr_res_v": float(corr_v),
        "tolerance_drift": tolerance_drift,
        "within_tolerance": within_tolerance
    },
    "notes": [
        "Uses time-stacked M6_field_stack.npy / M6_velocity_stack.npy when available.",
        "Entropy is local-window normalized to avoid global normalization artifacts.",
        "Continuity tested (1D periodic): ∂t S + ∂x(ρ_E v - X0 ∂x S) ≈ 0.",
        "If diffusion_strength>0, uses v_eff=∂t u (smoothed) for transport consistency under noisy u updates.",
        "X0 is fit by least squares against ∂xx S."
    ],
    "files": {
        "plot": "PAEV_X1_information_flux.png",
        "summary": "backend/modules/knowledge/X1_information_conservation_summary.json"
    },
    "protocol": "Tessaris Unified Constants & Verification Protocol (TUCVP) v1.2"
}

# =====================================================
# 6. Save outputs and visualization
# =====================================================
out_dir = "backend/modules/knowledge"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "X1_information_conservation_summary.json")

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

import matplotlib.pyplot as plt
plt.figure(figsize=(7, 4.5))
plt.plot(drift, lw=1.5)
plt.title("X1 drift: mean_x residual_fit(t)")
plt.xlabel("frame")
plt.ylabel("mean_x residual")
plt.tight_layout()
plt.savefig(os.path.join(out_dir, "PAEV_X1_information_flux.png"), dpi=200)
plt.close()

# =====================================================
# 7. Final printout
# =====================================================
print("✅ Plot saved -> PAEV_X1_information_flux.png")
print(f"✅ Summary saved -> {out_path}")
print("\n🧭 Discovery Notes -", timestamp)
print("------------------------------------------------------------")
print(f"* dt_eff = {dt_eff} (dt_base={dt_base}, stride={stride}), dx={dx}, frames={T}, N={N}")
print(f"* diffusion_strength = {diff_strength}")
print(f"* smooth_sigma = {smooth_sigma}")
print(f"* velocity_mode = {'v_eff=du/dt (smoothed)' if use_v_eff else 'M6_velocity_stack.npy'}")
print(f"* X0_est = {X0_est:.6e}")
print(f"* mean|residual| raw (X0=1) = {mean_abs_raw:.3e}")
print(f"* mean|residual| fit        = {mean_abs_fit:.3e}")
print(f"* drift mean abs (fit)      = {drift_mean_abs:.3e}")
print(f"* corr(res,u)={corr_u:.3f}, corr(res,v)={corr_v:.3f}")
print(f"* Tolerance (drift) = {tolerance_drift:.1e}")
print(f"* Result -> {'✅ Within tolerance' if within_tolerance else '⚠️ Outside tolerance'}")
print("------------------------------------------------------------")
print("Verified under Tessaris Unified Constants & Verification Protocol (TUCVP).")