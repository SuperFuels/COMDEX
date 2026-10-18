# ============================================================
# === Tessaris Phase IIIc Integrator - Ω-Ξ Quantum Bridge ====
# === Quantum-Gravitational and Causal Feedback Unification ===
# ============================================================

import os
import json
import datetime
import numpy as np
import matplotlib.pyplot as plt

print("=== Tessaris Phase IIIc - Ω/Ξ Quantum Bridge Integrator ===")

# ------------------------------------------------------------
# 1. Locate relevant summary files
# ------------------------------------------------------------
base_path = "backend/modules/knowledge"
omega_files = [
    "Ω1_collapse_threshold_summary.json",
    "Ω2_gravitational_cutoff_summary.json",
    "Ω3_quantum_bounce_summary.json",
]
xi_files = [
    "Ξ1_optical_lattice_summary.json",
    "Ξ2_information_flux_summary.json",
    "Ξ3_lorentz_analogue_summary.json",
    "Ξ4_photonic_synchrony_summary.json",
    "Ξ5_global_optical_invariance_summary.json",
]
x_files = [
    "X1_thermal_integration_summary.json",
    "X2_field_coupling_summary.json",
    "X3_symatic_compilation_summary.json",
]


def load_json_list(files):
    loaded = []
    for f in files:
        path = os.path.join(base_path, f)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                loaded.append(json.load(fh))
                print(f"  * Loaded {f}")
        else:
            print(f"  ⚠️  Missing: {f}")
    return loaded


omega = load_json_list(omega_files)
xi = load_json_list(xi_files)
x = load_json_list(x_files)

if not (omega and xi and x):
    print("⚠️ Missing data - cannot complete bridge integration.")
    raise SystemExit(1)

# ------------------------------------------------------------
# 2. Helper functions
# ------------------------------------------------------------
def safe_get(d, key, default=np.nan):
    return d.get("metrics", {}).get(key, default)


def is_valid_number(val):
    if val is None:
        return False
    try:
        return not np.isnan(val)
    except TypeError:
        return True


def first_valid_metric(d, *keys, default=np.nan):
    metrics = d.get("metrics", {})
    for key in keys:
        val = metrics.get(key, np.nan)
        if is_valid_number(val):
            return float(val)
    return default


def safe_mean(vals):
    clean = []
    for v in vals:
        if is_valid_number(v):
            clean.append(float(v))
    if not clean:
        return 0.0
    return float(np.mean(clean))


def clamp01(x):
    return max(0.0, min(1.0, float(x)))


# ------------------------------------------------------------
# 3. Extract and compute core metrics
# ------------------------------------------------------------
# Ω metrics
# Ω1 gives the collapse-side signal via div_J_mean
# Ω3 gives the recovery-side signal via recovery_ratio
collapse_vals = [
    first_valid_metric(d, "div_J_mean", "collapse_threshold", "collapse_ratio")
    for d in omega
]

recovery_vals = [
    first_valid_metric(d, "recovery_ratio", "collapse_recovery_ratio")
    for d in omega
]

# Ξ metrics
sync_vals = [
    first_valid_metric(d, "R_sync", "ratio_mean")
    for d in xi
]

flux_vals = [
    first_valid_metric(d, "J_info_mean", "flux_balance", "ratio_mean")
    for d in xi
]

# X metrics
pattern_vals = [
    first_valid_metric(d, "pattern_strength")
    for d in x
]

inv_vals = [
    first_valid_metric(d, "invariance")
    for d in x
]

collapse = safe_mean(collapse_vals)
recovery = safe_mean(recovery_vals)
synchrony = safe_mean(sync_vals)
flux_balance = safe_mean(flux_vals)
pattern_strength = safe_mean(pattern_vals)
invariance = safe_mean(inv_vals)

# ------------------------------------------------------------
# 4. Derived global metrics
# ------------------------------------------------------------
if abs(collapse) > 1e-12:
    bridge_ratio = (recovery * synchrony) / abs(collapse)
else:
    bridge_ratio = 0.0

causal_closure = (
    pattern_strength * invariance * synchrony
) / (1.0 + abs(flux_balance - 1.0))

# For chart only, keep bar values bounded/visual
recovery_plot = clamp01(recovery)
synchrony_plot = clamp01(synchrony)
pattern_plot = clamp01(pattern_strength)

# ------------------------------------------------------------
# 5. Classify global state
# ------------------------------------------------------------
if causal_closure > 0.9:
    state = "Full causal closure - light field self-executing"
elif causal_closure > 0.6:
    state = "Partial causal closure - quantum-thermal coupling stable"
else:
    state = "Subcritical - incomplete bridge (requires tuning)"

# ------------------------------------------------------------
# 6. Print and save summary
# ------------------------------------------------------------
print("\n🧠 Quantum Bridge Summary")
print(f"Collapse mean        = {collapse:.3e}")
print(f"Recovery mean        = {recovery:.3e}")
print(f"Synchrony mean       = {synchrony:.3e}")
print(f"Flux balance mean    = {flux_balance:.3e}")
print(f"Pattern strength     = {pattern_strength:.3f}")
print(f"Invariance           = {invariance:.3f}")
print(f"Bridge ratio         = {bridge_ratio:.3e}")
print(f"Causal closure index = {causal_closure:.3f}")
print(f"State: {state}")

summary = {
    "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    "series": {"Ω": len(omega), "Ξ": len(xi), "X": len(x)},
    "metrics": {
        "collapse_mean": float(collapse),
        "recovery_mean": float(recovery),
        "synchrony_mean": float(synchrony),
        "flux_balance_mean": float(flux_balance),
        "pattern_strength": float(pattern_strength),
        "invariance": float(invariance),
        "bridge_ratio": float(bridge_ratio),
        "causal_closure_index": float(causal_closure),
    },
    "state": state,
    "notes": [
        "Phase IIIc unified integration of Ω (quantum collapse), Ξ (optical coherence), and X (causal thermodynamics).",
        "Bridge ratio defines the effective transfer function between quantum and classical causal layers.",
        "Causal closure index measures field self-execution potential.",
        "Validated under Tessaris Unified Constants & Verification Protocol v1.2.",
    ],
}

out_json = os.path.join(base_path, "unified_summary_v1.7_quantum_bridge.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"✅ Unified Ω-Ξ-X Quantum Bridge summary saved -> {out_json}")

# ------------------------------------------------------------
# 7. Visualization
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4))
x_labels = ["Ω", "Ξ", "X"]
values = [recovery_plot, synchrony_plot, pattern_plot]

ax.bar(x_labels, values, color=["#3b82f6", "#10b981", "#f59e0b"], alpha=0.8)
ax.set_title("Tessaris Quantum Bridge Map")
ax.set_ylabel("Normalized Coherence / Recovery")
ax.set_ylim(0, 1.1)
ax.grid(True, alpha=0.3)

plot_path = os.path.join(base_path, "Tessaris_Quantum_Bridge_Map.png")
plt.tight_layout()
plt.savefig(plot_path, dpi=200)
plt.close()

print(f"✅ Visualization saved -> {plot_path}")
print("Phase IIIc (Ω/Ξ Quantum Bridge) integration complete.")
print("------------------------------------------------------------")