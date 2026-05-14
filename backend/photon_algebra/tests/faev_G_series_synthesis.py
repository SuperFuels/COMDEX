# ==========================================================
# G-Series Synthesis Report - Tessaris Unified Equation (TUE)
# Consolidates all G-level JSONs (G1 ... G4RC4)
# Builds stability progression, coupling histogram,
# and registry metadata summary.
# Saves: backend/modules/knowledge/G_series_synthesis.json
# ==========================================================

import os, json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone

base_dir = "backend/modules/knowledge"
out_path = os.path.join(base_dir, "G_series_synthesis.json")

# ---- Collect all G-series files ----
files = [f for f in os.listdir(base_dir)
         if f.startswith("G") and f.endswith(".json") and not f.endswith("synthesis.json")]

records = []
for f in sorted(files):
    try:
        with open(os.path.join(base_dir, f)) as fp:
            data = json.load(fp)
            metrics = data.get("metrics", {})
            rec = {
                "name": f.replace(".json", ""),
                "stability": metrics.get("energy_stability"),
                "corr_S_I": metrics.get("corr_S_I")
                            or metrics.get("entropy_info_correlation")
                            or metrics.get("cross_correlation_R_I"),
                "classification": data.get("classification"),
                "timestamp": data.get("timestamp")
            }
            records.append(rec)
    except Exception as e:
        print(f"[warn] Failed to load {f}: {e}")

# ---- Build progression arrays ----
names = [r["name"] for r in records]
stabilities = [r["stability"] for r in records]

# handle correlations safely (replace None with np.nan)
corrs = [r["corr_S_I"] if isinstance(r["corr_S_I"], (int, float)) else np.nan for r in records]

# ---- Plot 1: stability progression ----
plt.figure(figsize=(9,5))
plt.plot(names, stabilities, "o-", lw=1.5)
plt.title("G-Series Stability Progression")
plt.xlabel("Experiment"); plt.ylabel("Energy Stability"); plt.grid(True, alpha=0.3)
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(base_dir, "G_series_stability_progression.png"))

# ---- Plot 2: coupling correlation ----
plt.figure(figsize=(9,5))
valid_idx = [i for i, c in enumerate(corrs) if not np.isnan(c)]
if valid_idx:
    plt.bar([names[i] for i in valid_idx], [corrs[i] for i in valid_idx],
            color="purple", alpha=0.7)
    plt.title("G-Series Entropy-Information Coupling Strength")
    plt.xlabel("Experiment"); plt.ylabel("corr(S,I)")
    plt.xticks(rotation=30, ha="right"); plt.tight_layout()
    plt.savefig(os.path.join(base_dir, "G_series_coupling_histogram.png"))
else:
    print("[warn] No valid correlation data found; skipping coupling plot.")

# ---- Summary metrics ----
valid_stabs = [s for s in stabilities if isinstance(s, (int,float))]
mean_stab = float(np.nanmean(valid_stabs)) if valid_stabs else None
best_idx = int(np.nanargmax(valid_stabs)) if valid_stabs else -1
best_name = names[best_idx] if best_idx >= 0 else None

summary = {
    "series": "G",
    "count": len(records),
    "mean_stability": mean_stab,
    "best_experiment": best_name,
    "records": records,
    "files": {
        "stability_plot": "G_series_stability_progression.png",
        "coupling_plot": "G_series_coupling_histogram.png"
    },
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
}

with open(out_path, "w") as f:
    json.dump(summary, f, indent=2)

print("=== G-Series Synthesis Complete ===")
print(f"{len(records)} records merged | mean stability={mean_stab:.3f}")
print(f"Best run -> {best_name}")
print(f"✅ Saved -> {out_path}")