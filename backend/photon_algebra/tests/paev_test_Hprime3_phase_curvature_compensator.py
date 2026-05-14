#!/usr/bin/env python3
"""
Test H′3 - Tessaris Phase-Curvature Compensation
Applies curvature correction to stabilize field drift using G′ curvature deltas.
Inputs: 
  - H′1 recalibrated cohesion data
  - G′ lock snapshot (baseline)
Outputs:
  - H′3 compensated JSON and CSV
  - Updated plot showing phase-corrected temporal stability
"""

import os, json, csv, time
import numpy as np
import matplotlib.pyplot as plt

# --- Input and output paths ---
COH_FILE = "backend/photon_algebra/constants/Hprime1_field_cohesion_recalibrated.json"
LOCK_FILE = "backend/photon_algebra/constants/Gprime_lock_snapshot.json"
OUTPUT_JSON = "backend/photon_algebra/constants/Hprime3_phase_curvature_compensated.json"
OUTPUT_CSV = "backend/photon_algebra/tests/results_Hprime3_phase_curvature_compensated.csv"
PLOT_FILE = "backend/photon_algebra/tests/PAEV_TestHprime3_Compensation.png"

# --- Utility ---
def load_json(path):
    if not os.path.exists(path):
        print(f"⚠️ Missing file: {path}")
        return {}
    with open(path) as f:
        return json.load(f)

def normalize(v):
    return (v - np.min(v)) / (np.max(v) - np.min(v)) if np.max(v) != np.min(v) else v

def main():
    print("=== H′3 - Tessaris Phase-Curvature Compensation ===")

    coh = load_json(COH_FILE)
    lock = load_json(LOCK_FILE)
    if not coh or not lock:
        print("🚨 Missing inputs - ensure recalibrated H′1 and G′ lock snapshot exist.")
        return

    phases = coh.get("phases", {})
    deltas = coh.get("deltas", {})
    curvature_terms = {}

    # --- Extract curvature corrections from G′ constants ---
    for k in ("alpha", "hbar", "m_e", "G"):
        if k in lock:
            curvature_terms[k] = np.sqrt(abs(lock[k])) * 1e-6  # simplified curvature proxy

    # --- Apply curvature-phase coupling correction ---
    corrected_phases = {}
    corrected_deltas = {}
    for k in phases.keys():
        phi = phases[k]
        dphi = deltas[k]
        curvature = curvature_terms.get(k, 0)
        # Compensation factor derived from curvature gradient influence
        comp = 1 / (1 + curvature * 1e3)
        corrected_phases[k] = phi * comp
        corrected_deltas[k] = dphi * comp

    # --- Compute new stability metrics ---
    fci_values = np.array(list(corrected_deltas.values()))
    mean_fci = np.sqrt(np.mean(fci_values ** 2)) * 100
    std_fci = np.std(fci_values) * 100
    tsi = (100 / (1 + std_fci)) * np.exp(-mean_fci / 100)

    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "corrected_phases": corrected_phases,
        "corrected_deltas": corrected_deltas,
        "mean_FCI": mean_fci,
        "std_FCI": std_fci,
        "TSI": tsi
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(result, f, indent=4)

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Constant", "Phase(rad)", "Δφ(rad)"])
        for k in corrected_phases.keys():
            writer.writerow([k, corrected_phases[k], corrected_deltas[k]])
        writer.writerow(["Mean_FCI(%)", mean_fci])
        writer.writerow(["Std_FCI(%)", std_fci])
        writer.writerow(["TSI", tsi])

    # --- Polar plot visualization ---
    labels = list(corrected_phases.keys())
    values = [abs(corrected_deltas[k]) for k in labels]
    values += values[:1]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    plt.figure(figsize=(6,6))
    ax = plt.subplot(111, polar=True)
    ax.plot(angles, values, "r-", linewidth=2)
    ax.fill(angles, values, "r", alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_title(f"H′3 - Phase-Curvature Compensation (TSI={tsi:.3f}%)")
    plt.tight_layout()
    plt.savefig(PLOT_FILE)

    # --- Display summary ---
    print(f"📘 Saved compensated JSON -> {OUTPUT_JSON}")
    print(f"📄 Saved compensated CSV -> {OUTPUT_CSV}")
    print(f"📈 Saved plot -> {PLOT_FILE}")
    print(f"✅ Phase-Curvature Compensation complete.")
    print(f"   Mean FCI = {mean_fci:.3f} %, Std = {std_fci:.3f} %, TSI = {tsi:.3f} %")

if __name__ == "__main__":
    main()