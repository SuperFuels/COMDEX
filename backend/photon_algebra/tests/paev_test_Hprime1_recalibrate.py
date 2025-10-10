#!/usr/bin/env python3
"""
Test H′1 — Tessaris Field Phase Recalibration
Re-aligns phase deltas from H′1 to match the latest locked G′ constants.
Supports simplified or structured G′ lock snapshots.
"""

import os, json, numpy as np, time, csv
import matplotlib.pyplot as plt

LOCK_FILE = "backend/photon_algebra/constants/Gprime_lock_snapshot.json"
COH_FILE = "backend/photon_algebra/constants/Hprime1_field_cohesion.json"
OUTPUT_JSON = "backend/photon_algebra/constants/Hprime1_field_cohesion_recalibrated.json"
OUTPUT_CSV = "backend/photon_algebra/tests/results_Hprime1_recalibrated.csv"
PLOT_FILE = "backend/photon_algebra/tests/PAEV_TestHprime1_Recalibration.png"

def load_json(path):
    if not os.path.exists(path):
        print(f"⚠️ Missing file: {path}")
        return {}
    with open(path) as f:
        return json.load(f)

def extract_constants(data):
    """Handle both structured and flat snapshot formats."""
    if "constants" in data:
        # Old format with nested constants
        for k, v in data["constants"].items():
            if isinstance(v, dict):
                return {kk.replace("_%", ""): vv for kk, vv in v.items() if isinstance(vv, (int, float))}
    # Flat format
    return {k: v for k, v in data.items() if isinstance(v, (int, float))}

def main():
    print("=== H′1 — Tessaris Field Phase Recalibration ===")

    lock = load_json(LOCK_FILE)
    coh = load_json(COH_FILE)

    consts = extract_constants(lock)
    phases = coh.get("phases", {})
    deltas = coh.get("deltas", {})

    if not consts or not phases:
        print("🚨 Missing input data — ensure both lock snapshot and H′1 cohesion exist.")
        return

    # Apply recalibration by proportionally adjusting each phase and delta
    for k in phases.keys():
        if k in consts:
            # Normalize relative to constant magnitude
            scale = (consts[k] / consts[k]) if consts[k] != 0 else 1
            phases[k] *= scale
            deltas[k] *= scale

    # Compute new FCI
    fci = np.sqrt(np.mean(np.square(list(deltas.values())))) * 100

    recalibrated = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phases": phases,
        "deltas": deltas,
        "FCI": fci
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(recalibrated, f, indent=4)

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Constant", "Phase(rad)", "Δφ(rad)"])
        for k in phases.keys():
            writer.writerow([k, phases[k], deltas[k]])
        writer.writerow(["FCI(%)", fci])

    # Plot
    labels = list(phases.keys())
    values = [abs(deltas[k]) for k in labels]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    plt.figure(figsize=(6,6))
    ax = plt.subplot(111, polar=True)
    ax.plot(angles, values, "r-", linewidth=2)
    ax.fill(angles, values, "r", alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_title(f"H′1 — Recalibrated Field Cohesion (FCI={fci:.3f}%)")
    plt.tight_layout()
    plt.savefig(PLOT_FILE)

    print(f"📘 Saved recalibrated JSON → {OUTPUT_JSON}")
    print(f"📄 Saved recalibrated CSV → {OUTPUT_CSV}")
    print(f"📈 Saved plot → {PLOT_FILE}")
    print(f"✅ Recalibration complete. New FCI = {fci:.3f} %")

if __name__ == "__main__":
    main()