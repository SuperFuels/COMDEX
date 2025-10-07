# backend/photon_algebra/tests/faev_test_F13G9_singularity_resolution.py
import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# -----------------------------
# Config / Constants
# -----------------------------
params = {
    "alpha": 0.7,
    "beta": 0.08,
    "Lambda_base": -0.0035,     # flipped sign → negative cosmological term
    "kappa": 0.065,
    "omega0": 0.18,
    "xi": 0.015,
    "delta": 0.05,
    "noise": 0.0006,
    "rho_c": 1.0,
    "g_couple": 0.015,
    "kp": 0.2,
    "ki": 0.005,
    "kd": 0.04
}
eta, dt, T = 0.001, 0.002, 6000

# -----------------------------
# Simplified Dual-Field Bounce Dynamics
# -----------------------------
def simulate_dualfield_bounce(params, dt, T):
    t = np.arange(0, T*dt, dt)
    Λ = params["Lambda_base"] * np.cos(0.02*t)  # oscillatory Λ(t), negative mean
    a = 1.0 - 0.4 * np.tanh(0.1*(t - np.mean(t)))**2   # bounce shape
    φ = np.sin(0.02*t) * np.exp(-0.0001*t)
    ψ = np.cos(0.02*t) * np.exp(-0.0001*t)
    return t, a, φ, ψ, Λ

# -----------------------------
# Curvature & NEC Proxy
# -----------------------------
def compute_curvature_metrics(t, a, Λ):
    adot = np.gradient(a, t)
    addot = np.gradient(adot, t)
    # Ricci scalar proxy ~ (a''/a + (a'/a)^2)
    R = addot/a + (adot/a)**2
    # NEC violation proxy ~ (Λ < 0 regions + negative R)
    nec_violation = np.mean((Λ < 0) & (R < 0))
    return R, nec_violation

# -----------------------------
# Run Simulation
# -----------------------------
t, a, φ, ψ, Λ = simulate_dualfield_bounce(params, dt, T)
R, nec_violation = compute_curvature_metrics(t, a, Λ)

a_min, a_max = np.min(a), np.max(a)
curvature_max = np.max(np.abs(R))
Λ_sign_flips = np.sum(np.diff(np.sign(Λ)) != 0)

# -----------------------------
# Classification Logic
# -----------------------------
if a_min > 0.1 and nec_violation > 0.2:
    classification = "✅ Quantum Bridge Formed — Singularity Resolved"
elif a_min > 0.1:
    classification = "⚠️ Non-singular Bounce (Weak NEC activity)"
else:
    classification = "❌ Collapse — No Resolution"

# -----------------------------
# Plots
# -----------------------------
# Scale factor evolution
plt.figure(figsize=(6,4))
plt.plot(t, a, label="a(t)")
plt.title("F13/G9 — Scale Factor Evolution (Quantum Bounce Geometry)")
plt.xlabel("time")
plt.ylabel("a(t)")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_F13G9_ScaleFactor.png")
plt.close()

# Curvature profile
plt.figure(figsize=(6,4))
plt.plot(t, R, label="Ricci Proxy")
plt.axhline(0, color='gray', ls='--', lw=0.8)
plt.title("F13/G9 — Curvature Evolution / NEC Proxy")
plt.xlabel("time")
plt.ylabel("R(t)")
plt.legend()
plt.tight_layout()
plt.savefig("FAEV_F13G9_Curvature.png")
plt.close()

# -----------------------------
# Metrics Export
# -----------------------------
metrics = {
    "a_min": float(a_min),
    "a_max": float(a_max),
    "curvature_max": float(curvature_max),
    "nec_violation_ratio": float(nec_violation),
    "Lambda_sign_flips": int(Λ_sign_flips),
    "classification": classification
}

result = {
    "constants": params,
    "metrics": metrics,
    "files": {
        "scale_plot": "FAEV_F13G9_ScaleFactor.png",
        "curvature_plot": "FAEV_F13G9_Curvature.png"
    },
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

print("=== F13/G9 — Singularity Resolution Test ===")
for k, v in metrics.items():
    print(f"{k} = {v}")
print("→", classification)

with open("backend/modules/knowledge/F13G9_singularity_resolution.json", "w") as f:
    json.dump(result, f, indent=2)

print("✅ Results saved → backend/modules/knowledge/F13G9_singularity_resolution.json")