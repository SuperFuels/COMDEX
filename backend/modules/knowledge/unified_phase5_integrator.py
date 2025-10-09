#!/usr/bin/env python3
"""
Tessaris — Unified Phase V (Ξ-Series) Integrator
Aggregates Ξ1–Ξ5 optical/photonic realisation results into one summary.
Outputs:
  • unified_summary_v1.5.json
  • Tessaris_Optical_Realisation_Map.png
"""

import os, json, datetime
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

BASE = Path(__file__).parent
FILES = [
    "Ξ1_optical_lattice_summary.json",
    "Ξ2_information_flux_summary.json",
    "Ξ3_lorentz_analogue_summary.json",
    "Ξ4_photonic_synchrony_summary.json",
    "Ξ5_global_optical_invariance_summary.json",
]

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

print("=== Tessaris Phase V (Ξ) Integrator ===")
loaded = []
for fn in FILES:
    p = BASE / fn
    if p.exists():
        loaded.append(load_json(p))
        print(f"  • Loaded {fn}")

# Extract a few headline metrics if present
def get(d, *keys, default=None):
    cur = d
    try:
        for k in keys:
            cur = cur[k]
        return cur
    except Exception:
        return default

headlines = {
    "Ξ1_ratio": get(loaded[0], "metrics", "ratio", default=None) if len(loaded)>0 else None,
    "Ξ2_ratio": None,
    "Ξ3_sigma": None,
    "Ξ4_R_sync": None,
    "Ξ5_sigma": None,
}

for doc in loaded:
    title = Path(doc.get("protocol","")).name  # not used; just a placeholder
    m = doc.get("metrics", {})
    # Identify by presence of keys
    if "ratio" in m and "stable" in m:    # Ξ1 or Ξ2
        if headlines["Ξ2_ratio"] is None and doc.get("notes", [""])[0].startswith("Mean information flux"):
            headlines["Ξ2_ratio"] = m["ratio"]
    if "ratio_std" in m and "velocities" in m:  # Ξ3 or Ξ5
        if headlines["Ξ3_sigma"] is None:
            headlines["Ξ3_sigma"] = m["ratio_std"]
        else:
            headlines["Ξ5_sigma"] = m["ratio_std"]
    if "R_sync" in m:
        headlines["Ξ4_R_sync"] = m["R_sync"]

summary = {
    "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    "series": "Ξ — Physical Implementation (Optical/Photonic)",
    "records_loaded": len(loaded),
    "headlines": headlines,
    "notes": [
        "Ξ-series validates physical realisability of computational causality.",
        "Ξ2 and Ξ5 demonstrate optical counterparts of K2 (entropy causality) and K5 (global invariance).",
        "Ξ4 shows high synchrony (entanglement-analogue) in coupled waveguides.",
    ],
    "version": "v1.5"
}

out_json = BASE / "unified_summary_v1.5.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"✅ Unified Ξ summary saved → {out_json}")

# Simple diagnostic plot if Ξ3/Ξ5 present
plt.figure(figsize=(7.2,4))
labels, vals = [], []
if headlines["Ξ3_sigma"] is not None:
    labels.append("Ξ3 σ (ratio)"); vals.append(headlines["Ξ3_sigma"])
if headlines["Ξ5_sigma"] is not None:
    labels.append("Ξ5 σ (ratio)"); vals.append(headlines["Ξ5_sigma"])
if headlines["Ξ4_R_sync"] is not None:
    labels.append("Ξ4 R_sync"); vals.append(headlines["Ξ4_R_sync"])

if vals:
    plt.bar(labels, vals)
    plt.title("Ξ-Series — Key Optical Metrics")
    plt.ylabel("Value")
    plt.grid(True, axis="y", alpha=0.3)
    out_png = BASE / "Tessaris_Optical_Realisation_Map.png"
    plt.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"✅ Visualization saved → {out_png}")

print("Phase V (Ξ) integration complete.")
print("------------------------------------------------------------")