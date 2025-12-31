import os, json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# --- constants ---
from backend.photon_algebra.utils.load_constants import load_constants
const = load_constants()
ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

# --- load O1-O10 summaries ---
knowledge_dir = "backend/modules/knowledge"
O_files = [f for f in os.listdir(knowledge_dir) if f.startswith("O") and f.endswith(".json")]
O_data = []

for f in sorted(O_files):
    with open(os.path.join(knowledge_dir, f)) as jf:
        try:
            O_data.append(json.load(jf))
        except Exception as e:
            print(f"⚠️ Could not read {f}: {e}")

# --- extract metrics ---
drifts, correlations = [], []
for d in O_data:
    for key in d.keys():
        if "drift" in key or "mean_drift" in key:
            drifts.append(d[key])
        if "corr" in key or "correlation" in key:
            correlations.append(d[key])

drifts = np.array(drifts)
correlations = np.array(correlations)

ΔC_total = np.sum(drifts)
C_corr = np.mean(correlations)
CI = np.exp(-abs(ΔC_total)) * (C_corr ** 2)

# --- classification ---
if abs(ΔC_total) < 1e-4 and CI > 0.95:
    cls = "✅ Causally convergent equilibrium"
elif abs(ΔC_total) < 5e-4:
    cls = "⚠️ Marginal causal drift"
else:
    cls = "❌ Divergent causal flow"

# --- plot ---
plt.figure(figsize=(8,5))
plt.bar(range(len(drifts)), drifts, color="steelblue", alpha=0.7)
plt.axhline(0, color='k', linestyle='--', linewidth=0.8)
plt.title("O11 - Causal Convergence Validation")
plt.xlabel("Module index (O1-O10)")
plt.ylabel("Drift (ΔS)")
plt.tight_layout()
plt.savefig("PAEV_O11_CausalConvergence.png", dpi=120)

# --- save summary ---
summary = {
    "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
    "ΔC_total": float(ΔC_total),
    "C_corr": float(C_corr),
    "Convergence_Index": float(CI),
    "classification": cls,
    "files": {"plot": "PAEV_O11_CausalConvergence.png"},
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
}

out_path = os.path.join(knowledge_dir, "O11_causal_convergence.json")
with open(out_path, "w") as f:
    json.dump(summary, f, indent=2)

print("=== O11 - Causal Convergence Validation ===")
print(f"ΔC_total={ΔC_total:.3e} | Corr={C_corr:.3f} | CI={CI:.3f} -> {cls}")
print(f"✅ Results saved -> {out_path}")