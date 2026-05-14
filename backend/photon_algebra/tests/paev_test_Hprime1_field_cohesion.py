#!/usr/bin/env python3
"""
Test H′1 - Tessaris Field Phase Cohesion
Evaluates harmonic phase alignment between locked constants (G′ snapshot).
"""

import json, math, os, csv
import numpy as np
import matplotlib.pyplot as plt

LOCK_PATH = "backend/photon_algebra/constants/Gprime_lock_snapshot.json"
OUTPUT_JSON = "backend/photon_algebra/constants/Hprime1_field_cohesion.json"
OUTPUT_CSV = "backend/photon_algebra/tests/results_Hprime1_field_cohesion.csv"
OUTPUT_PLOT = "backend/photon_algebra/tests/PAEV_TestHprime1_FieldCohesion.png"

def load_constants():
    with open(LOCK_PATH) as f:
        return json.load(f)

def phase_transform(value, ref=1.0):
    """Project a scalar constant into harmonic phase space (mod 2π)."""
    try:
        norm = value / ref
        phase = (2 * math.pi * (math.log10(norm) % 1))
        return phase
    except Exception:
        return np.nan

def compute_cohesion(consts):
    refs = {
        "alpha": 7.2973525693e-3,
        "hbar": 1.054571817e-34,
        "m_e": 9.1093837015e-31,
        "G": 6.6743e-11,
    }
    phases = {k: phase_transform(v, refs[k]) for k, v in consts.items() if k in refs}
    deltas = {k: phases[k] - np.mean(list(phases.values())) for k in phases}
    rms = math.sqrt(np.mean([d**2 for d in deltas.values()]))
    FCI = rms / (2 * math.pi) * 100
    return phases, deltas, FCI

def save_results(phases, deltas, FCI):
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump({"phases": phases, "deltas": deltas, "FCI": FCI}, f, indent=2)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Constant", "Phase(rad)", "Δφ(rad)"])
        for k in phases:
            writer.writerow([k, f"{phases[k]:.6f}", f"{deltas[k]:.6f}"])
        writer.writerow(["FCI(%)", FCI])
    print(f"📄 Saved results -> {OUTPUT_CSV}")
    print(f"📘 Saved JSON -> {OUTPUT_JSON}")

def plot_cohesion(phases, deltas, FCI):
    labels = list(phases.keys())
    phase_vals = [phases[k] for k in labels]
    delta_vals = [deltas[k] for k in labels]
    theta = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.plot(theta, phase_vals, "r-", linewidth=2)
    ax.fill(theta, phase_vals, "r", alpha=0.3)
    ax.set_title(f"H′1 - Field Phase Cohesion Map (FCI={FCI:.3f}%)")
    plt.savefig(OUTPUT_PLOT, dpi=300)
    print(f"📈 Saved plot -> {OUTPUT_PLOT}")

def main():
    print("=== H′1 - Tessaris Field Phase Cohesion Test ===")
    consts = load_constants()
    phases, deltas, FCI = compute_cohesion(consts)
    print(f"Field Cohesion Index (FCI): {FCI:.3f} %")
    save_results(phases, deltas, FCI)
    plot_cohesion(phases, deltas, FCI)
    if FCI < 1.0:
        print("✅ Field harmonic alignment maintained.")
    elif FCI < 5.0:
        print("⚠️ Mild field phase drift - monitor under H′2.")
    else:
        print("🚨 Field incoherence detected - review G′ baseline.")

if __name__ == "__main__":
    main()