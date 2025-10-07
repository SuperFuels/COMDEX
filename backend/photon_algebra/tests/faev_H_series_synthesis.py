# ==========================================================
# H-Series Synthesis — Temporal Emergence Layer
# Consolidates all H*.json results (arrow of time, entropy flow)
# Saves: backend/modules/knowledge/H_series_synthesis.json
# ==========================================================

import os, json, numpy as np, matplotlib.pyplot as plt
from datetime import datetime, timezone

base_dir = "backend/modules/knowledge"
out_path = os.path.join(base_dir, "H_series_synthesis.json")

records = []
for f in os.listdir(base_dir):
    if f.startswith("H") and f.endswith(".json"):
        try:
            with open(os.path.join(base_dir, f)) as fp:
                data = json.load(fp)
            metrics = data.get("metrics", {})
            stab = metrics.get("energy_stability")
            records.append({
                "name": f,
                "stability": stab,
                "timestamp": data.get("timestamp")
            })
        except Exception:
            pass

stabilities = [r["stability"] for r in records if isinstance(r["stability"], (int, float))]
mean_stab = float(np.mean(stabilities)) if stabilities else None

plt.figure(figsize=(8,4))
plt.bar([r["name"].split(".")[0] for r in records], stabilities, color="gold", alpha=0.7)
plt.xticks(rotation=90, fontsize=7)
plt.title("H-Series Stability (Temporal Emergence)")
plt.tight_layout()
plt.savefig(os.path.join(base_dir, "H_series_stability.png"))

summary = {
    "series": "H",
    "series_type": "temporal_emergence",
    "count": len(records),
    "mean_stability": mean_stab,
    "best_experiment": records[np.argmax(stabilities)]["name"] if stabilities else None,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "summary_text": (
        "The H-series explores temporal emergence, entropy flow, and arrow-of-time coherence. "
        "This synthesis consolidates H-series tests (e.g., H1–H3) and evaluates their stability "
        "and phase-locking progression under unified constants."
    )
}

with open(out_path, "w") as f:
    json.dump(summary, f, indent=2)

print(f"=== H-Series Synthesis Complete ({len(records)} records) ===")
print(f"Mean stability = {mean_stab}")
print(f"✅ Saved → {out_path}")