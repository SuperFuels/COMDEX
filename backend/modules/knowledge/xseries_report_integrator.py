# ============================================================
# === Tessaris Phase IIIb Integrator — X-Series ==============
# === Quantum–Thermal–Causal Unification Report ==============
# ============================================================

import json, os, datetime
import numpy as np
import matplotlib.pyplot as plt

print("=== Tessaris Phase IIIb Integrator — X-Series (Tessaris) ===")

# ------------------------------------------------------------
# 1. Locate series summaries
# ------------------------------------------------------------
base_path = "backend/modules/knowledge"
summaries = [
    "X1_thermal_integration_summary.json",
    "X2_field_coupling_summary.json",
    "X3_symatic_compilation_summary.json"
]

loaded = []
for file in summaries:
    path = os.path.join(base_path, file)
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        loaded.append(data)
        print(f"  • Loaded {file}")
    else:
        print(f"  ⚠️  Missing: {file}")

if not loaded:
    raise FileNotFoundError("No X-Series summary files found!")

# ------------------------------------------------------------
# 2. Extract unified metrics
# ------------------------------------------------------------
def safe_get(d, key, default=np.nan):
    return d["metrics"].get(key, default)

E_means = [safe_get(d, "E_mean") for d in loaded if "E_mean" in d["metrics"]]
S_means = [safe_get(d, "S_mean") for d in loaded if "S_mean" in d["metrics"]]
balance = [safe_get(d, "balance_residual") for d in loaded]
coherence = [safe_get(d, "coherence") for d in loaded]
pattern_strength = [safe_get(d, "pattern_strength") for d in loaded]
invariance = [safe_get(d, "invariance") for d in loaded]

# Derived metrics
mean_E = np.nanmean(E_means)
mean_S = np.nanmean(S_means)
global_balance = np.nanmean(balance)
global_coherence = np.nanmean(coherence)
global_pattern_strength = np.nanmean(pattern_strength)
global_invariance = np.nanmean(invariance)

# ------------------------------------------------------------
# 3. Determine unified causal state
# ------------------------------------------------------------
if global_pattern_strength > 0.9 and global_invariance > 0.95:
    state = "Stable causal executable lattice"
elif global_pattern_strength > 0.8:
    state = "Partially executable — subcritical coherence"
else:
    state = "Non-executable — thermal imbalance persists"

collapse_recovery = 1.0 - abs(mean_E - mean_S) / (abs(mean_E) + 1e-9)

# ------------------------------------------------------------
# 4. Print and save unified summary
# ------------------------------------------------------------
print("\n🧠 X-Series Summary")
print(f"Mean ⟨E⟩ = {mean_E:.3e}, Mean ⟨S⟩ = {mean_S:.3e}")
print(f"Global balance residual = {global_balance:.3e}")
print(f"Global coherence = {global_coherence:.3f}")
print(f"Pattern strength = {global_pattern_strength:.3f}")
print(f"Invariance = {global_invariance:.3f}")
print(f"Collapse→Recovery ratio = {collapse_recovery:.3f}")
print(f"State: {state}")

summary = {
    "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    "series": ["X1", "X2", "X3"],
    "metrics": {
        "mean_E": float(mean_E),
        "mean_S": float(mean_S),
        "global_balance": float(global_balance),
        "global_coherence": float(global_coherence),
        "global_pattern_strength": float(global_pattern_strength),
        "global_invariance": float(global_invariance),
        "collapse_recovery_ratio": float(collapse_recovery),
    },
    "state": state,
    "notes": [
        "Unified X-Series analysis under Tessaris Unified Constants Protocol v1.2.",
        "Combines quantum–thermal integration, field–computational coupling, and symatic compilation.",
        "Collapse→Recovery ratio reflects degree of energy–entropy balance.",
        "Pattern strength and invariance define causal executability of the lattice.",
    ],
    "protocol": "Tessaris Unified Constants & Verification Protocol v1.2",
}

out_path = os.path.join(base_path, "unified_summary_v1.6.json")
with open(out_path, "w") as f:
    json.dump(summary, f, indent=2)
print(f"✅ Unified X-Series summary saved → {out_path}")

# ------------------------------------------------------------
# 5. Visualization
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7,4))
x_labels = ["X₁ Thermal", "X₂ Coupling", "X₃ Symatic"]
strengths = [np.nan_to_num(s, nan=0) for s in pattern_strength]
invs = [np.nan_to_num(i, nan=0) for i in invariance]

ax.plot(x_labels, strengths, marker="o", label="Pattern Strength")
ax.plot(x_labels, invs, marker="s", label="Invariance")
ax.set_title("Tessaris X-Series Integration Map")
ax.set_ylabel("Metric Value")
ax.set_ylim(0, 1.1)
ax.legend()
ax.grid(True, alpha=0.3)

plot_path = os.path.join(base_path, "Tessaris_XSeries_Integration_Map.png")
plt.tight_layout()
plt.savefig(plot_path, dpi=200)
plt.close()
print(f"✅ Visualization saved → {plot_path}")

print("Phase IIIb (X-Series) integration complete.")
print("------------------------------------------------------------")