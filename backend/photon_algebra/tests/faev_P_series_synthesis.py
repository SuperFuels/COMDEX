# ==========================================================
# P-Series Synthesis - Predictive Resonance Layer (Fixed)
# Auto-detects stability metrics and handles missing data.
# Saves: backend/modules/knowledge/P_series_synthesis.json
# ==========================================================

import os, json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone

base_dir = "backend/modules/knowledge"
out_path = os.path.join(base_dir, "P_series_synthesis.json")

records = []

# Accept multiple stability keys
STABILITY_KEYS = ["energy_stability", "stability_index", "phase_stability", "coherence_score"]

for f in os.listdir(base_dir):
    if f.startswith("P") and f.endswith(".json"):
        try:
            with open(os.path.join(base_dir, f)) as fp:
                data = json.load(fp)
            metrics = data.get("metrics", {})
            stab = None
            for k in STABILITY_KEYS:
                if k in metrics and isinstance(metrics[k], (int, float)):
                    stab = metrics[k]
                    break
            records.append({
                "name": f,
                "stability": stab,
                "timestamp": data.get("timestamp")
            })
        except Exception:
            pass

stabilities = [r["stability"] for r in records if isinstance(r["stability"], (int, float))]
mean_stab = float(np.mean(stabilities)) if stabilities else None

# ---- Plot if data exists ----
if stabilities:
    plt.figure(figsize=(8,4))
    plt.bar([r["name"].split(".")[0] for r in records if r["stability"] is not None],
            stabilities, color="magenta", alpha=0.7)
    plt.xticks(rotation=90, fontsize=7)
    plt.title("P-Series Stability (Predictive Resonance)")
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, "P_series_stability.png"))
else:
    print("[warn] No numeric stability values found; skipping plot.")

# ---- Summary ----
summary = {
    "series": "P",
    "series_type": "predictive_resonance",
    "count": len(records),
    "mean_stability": mean_stab,
    "best_experiment": (max(records, key=lambda r: r["stability"] or -9999)["name"]
                        if stabilities else None),
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "summary_text": (
        "The P-series models predictive resonance and global phase synchronization. "
        "This synthesis consolidates P-series tests (P1-P10) representing cognitive "
        "and anticipatory coupling within the unified field framework."
    )
}

with open(out_path, "w") as f:
    json.dump(summary, f, indent=2)

print(f"=== P-Series Synthesis Complete ({len(records)} records) ===")
print(f"Mean stability = {mean_stab}")
print(f"✅ Saved -> {out_path}")