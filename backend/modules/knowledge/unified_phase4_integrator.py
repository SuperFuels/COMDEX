# === Tessaris Phase IV Integrator ===
# Consolidates Ω1–Ω3 results (Collapse → Cutoff → Recovery)
# Produces unified causal-closure summary and visualization
# Complies with Tessaris Unified Constants & Verification Protocol v1.2

import os, json, datetime
import numpy as np
import matplotlib.pyplot as plt

# --- Determine working path automatically ---
base_path = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(base_path, "unified_summary_v1.4.json")

print("=== Tessaris Phase IV Integrator ===")

# --- 1. Load all Ω-series summaries ---
omega_files = [f for f in os.listdir(base_path) if f.startswith("Ω") and f.endswith("_summary.json")]
omega_files.sort()
if not omega_files:
    print("❌ No Ω-series summaries found in", base_path)
    exit(1)

data = []
for f in omega_files:
    path = os.path.join(base_path, f)
    with open(path, "r", encoding="utf-8") as j:
        entry = json.load(j)
    data.append(entry)
    print(f"  • Loaded {f}")

# --- 2. Merge constants (use last valid) ---
constants = data[-1].get("constants", {})

# --- 3. Extract key metrics ---
div_J_mean = data[0]["metrics"].get("div_J_mean", np.nan) if "Ω1" in omega_files[0] else np.nan
cutoff_mean = data[1]["metrics"].get("R_eff", np.nan) if len(data) > 1 else np.nan
recovery_ratio = data[-1]["metrics"].get("recovery_ratio", np.nan) if len(data) > 2 else np.nan

collapse_to_recovery_ratio = (recovery_ratio or 0) / (cutoff_mean or 1e-9)

# --- 4. Classification ---
if 0.8 <= collapse_to_recovery_ratio <= 1.2:
    phase_state = "Causal closure and recovery equilibrium achieved"
elif collapse_to_recovery_ratio > 1.2:
    phase_state = "Over-recovery regime — super-causal expansion"
else:
    phase_state = "Partial recovery — subcritical re-expansion"

print(f"\n🧠 Phase IV Summary")
print(f"Collapse→Recovery ratio = {collapse_to_recovery_ratio:.3f}")
print(f"State: {phase_state}")

# --- 5. Unified summary ---
timestamp = datetime.datetime.now(datetime.UTC).isoformat()
summary = {
    "timestamp": timestamp,
    "phase": "Ω-series (Collapse → Recovery)",
    "constants": constants,
    "integrated_metrics": {
        "collapse_to_recovery_ratio": float(collapse_to_recovery_ratio),
        "collapse_div_J_mean": div_J_mean,
        "cutoff_R_eff": cutoff_mean,
        "recovery_ratio": recovery_ratio
    },
    "files_included": omega_files,
    "phase_state": phase_state,
    "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"✅ Unified Phase IV summary saved → {output_file}")

# --- 6. Visualization ---
labels = ["Ω1 Collapse", "Ω2 Cutoff", "Ω3 Recovery"]
values = [
    div_J_mean or 0,
    cutoff_mean or 0,
    recovery_ratio or 0,
]

plt.figure(figsize=(7, 4))
plt.bar(labels, values, color=["#d9534f", "#f0ad4e", "#5cb85c"])
plt.title("Tessaris Ω-Series — Collapse to Recovery Progression")
plt.ylabel("Normalized metric amplitude")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plot_path = os.path.join(base_path, "Tessaris_Collapse_Map.png")
plt.savefig(plot_path, dpi=200)
plt.close()

print(f"✅ Visualization saved → {plot_path}")
print("Phase IV integration complete.")
print("------------------------------------------------------------")