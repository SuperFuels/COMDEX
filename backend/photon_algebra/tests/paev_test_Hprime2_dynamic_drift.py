#!/usr/bin/env python3
"""
Test H′2 — Tessaris Dynamic Drift Monitor
Evaluates the stability of field phase cohesion (FCI) under small perturbations.
"""

import json, os, numpy as np, csv, time, math
import matplotlib.pyplot as plt

LOCK_FILE = "backend/photon_algebra/constants/Gprime_lock_snapshot.json"
COH_FILE = "backend/photon_algebra/constants/Hprime1_field_cohesion.json"
RESULTS_FILE = "backend/photon_algebra/tests/results_Hprime2_dynamic_drift.csv"
PLOT_FILE = "backend/photon_algebra/tests/PAEV_TestHprime2_Drift.png"

DRIFT_STEPS = np.linspace(-0.005, 0.005, 25)  # ±0.5% drift

def load_json(path):
    if not os.path.exists(path):
        print(f"⚠️ Missing file: {path}")
        return {}
    with open(path) as f:
        return json.load(f)

def compute_FCI_shift(constants, deltas):
    """Simulate new FCI based on perturbed constants."""
    vals = []
    for k in ("alpha", "hbar", "m_e", "G"):
        if k not in constants:
            continue
        phase = constants[k] * (1 + deltas.get(k, 0))
        vals.append(math.sin(phase * 1e6) ** 2)
    return np.mean(vals) * 100  # pseudo FCI %

def main():
    print("=== H′2 — Tessaris Dynamic Drift Monitor ===")

    base_constants = load_json(LOCK_FILE)
    base_phases = load_json(COH_FILE).get("phases", {})

    if not base_constants or not base_phases:
        print("🚨 Missing input data — ensure G′ lock and H′1 cohesion files exist.")
        return

    results = []
    for d in DRIFT_STEPS:
        deltas = {k: d for k in base_phases.keys()}
        fci = compute_FCI_shift(base_phases, deltas)
        results.append((d * 100, fci))

    drift_vals, fci_vals = zip(*results)
    mean_fci = np.mean(fci_vals)
    std_fci = np.std(fci_vals)

    # Save CSV
    with open(RESULTS_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Drift_%", "FCI_%"])
        for d, fci in results:
            writer.writerow([d, fci])
    print(f"📄 Saved drift results → {RESULTS_FILE}")

    # Plot
    plt.figure(figsize=(7,4))
    plt.plot(drift_vals, fci_vals, "r-", linewidth=2)
    plt.xlabel("Constant Drift (%)")
    plt.ylabel("FCI (%)")
    plt.title(f"H′2 — Dynamic Drift Stability (mean={mean_fci:.3f}%, σ={std_fci:.3f}%)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(PLOT_FILE)
    print(f"📈 Saved plot → {PLOT_FILE}")

    if std_fci < 0.5:
        print("✅ Field stability maintained — coherent drift response.")
    elif std_fci < 2.0:
        print("⚠️ Moderate drift — partial decoherence risk.")
    else:
        print("🚨 High instability detected — recheck phase mapping.")

    print(f"Mean FCI = {mean_fci:.3f} %, Std Dev = {std_fci:.3f} %")

if __name__ == "__main__":
    main()