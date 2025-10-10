#!/usr/bin/env python3
"""
Test H′5 — Tessaris Resonance Fine-Lock
Performs micro-phase refinement on the H′4 temporal lock using adaptive damping.
Finalizes the Tessaris Temporal Coherence Layer (TTCL).
"""

import os, json, csv, time
import numpy as np
import matplotlib.pyplot as plt

H4_FILE     = "backend/photon_algebra/constants/Hprime4_temporal_resonance_lock.json"
CONST_FILE  = "backend/photon_algebra/constants/paev_constants.json"
DISCOVERY_FILE = "backend/photon_algebra/tests/discoveries.json"
OUT_JSON    = "backend/photon_algebra/constants/Hprime5_resonance_finelock.json"
OUT_CSV     = "backend/photon_algebra/tests/results_Hprime5_resonance_finelock.csv"
OUT_PLOT    = "backend/photon_algebra/tests/PAEV_TestHprime5_FineLock.png"

# Fine sweep: small perturbations around H′4 parameters
GAIN_DELTA  = np.linspace(-0.15, 0.15, 11)
HARMONIC_DELTA = [-0.25, 0.0, 0.25]

def load_json(path):
    if not os.path.exists(path):
        print(f"⚠️ Missing: {path}")
        return {}
    with open(path) as f:
        return json.load(f)

def compute_RCI(values):
    arr = np.array(list(values.values()))
    if len(arr) == 0:
        return 0.0
    arr -= np.mean(arr)
    return float(np.clip(100 / (1 + np.std(arr) * 50), 0, 100))

def fine_lock_refine(h4):
    phases = h4.get("locked_phases", {})
    deltas = h4.get("locked_deltas", {})
    base_gain = h4["search"]["best_gain"]
    base_harm = h4["search"]["best_harmonic"]

    best = {"RCI": -1, "gain": None, "harmonic": None,
            "phases": None, "deltas": None}
    for dg in GAIN_DELTA:
        for dh in HARMONIC_DELTA:
            g = base_gain + dg
            h = base_harm + dh
            refined_phases, refined_deltas = {}, {}
            for k in phases:
                damp = np.cos(g * h * np.pi / 2.0)
                refined_phases[k] = phases[k] * damp
                refined_deltas[k] = deltas[k] * damp
            R = compute_RCI(refined_phases)
            if R > best["RCI"]:
                best.update(RCI=R, gain=g, harmonic=h,
                            phases=refined_phases, deltas=refined_deltas)
    return best

def radar_plot(phases, RCI):
    labels = list(phases.keys())
    vals = [abs(phases[k]) for k in labels] + [abs(phases[labels[0]])]
    angs = np.linspace(0, 2*np.pi, len(labels)+1)
    plt.figure(figsize=(6,6))
    ax = plt.subplot(111, polar=True)
    ax.plot(angs, vals, "r-", linewidth=2)
    ax.fill(angs, vals, "r", alpha=0.25)
    ax.set_xticks(angs[:-1])
    ax.set_xticklabels(labels)
    ax.set_title(f"H′5 — Resonance Fine-Lock (RCI₍fine₎={RCI:.3f}%)")
    plt.tight_layout()
    plt.savefig(OUT_PLOT)

def persist(result):
    const = load_json(CONST_FILE)
    const["Hprime5"] = {
        "timestamp": result["timestamp"],
        "RCI_fine_%": result["RCI_fine"],
        "Unified_Coherence_Index_%": result["UCI"],
        "best_gain": result["search"]["best_gain"],
        "best_harmonic": result["search"]["best_harmonic"]
    }
    with open(CONST_FILE, "w") as f:
        json.dump(const, f, indent=4)

    discoveries = load_json(DISCOVERY_FILE)
    if isinstance(discoveries, list):
        discoveries.append(result)
    elif isinstance(discoveries, dict) and "discoveries" in discoveries:
        discoveries["discoveries"].append(result)
    else:
        discoveries = [result]
    with open(DISCOVERY_FILE, "w") as f:
        json.dump(discoveries, f, indent=4)

    print(f"📘 Discovery ledger updated → {DISCOVERY_FILE}")
    print(f"📗 Constants registry updated → {CONST_FILE}")

def main():
    print("=== H′5 — Tessaris Resonance Fine-Lock ===")
    h4 = load_json(H4_FILE)
    if not h4:
        print("🚨 Missing H′4 temporal resonance data.")
        return

    best = fine_lock_refine(h4)
    RCI_fine = best["RCI"]
    TSI_prev = h4.get("TSI_inherit", 0)
    UCI = (RCI_fine + TSI_prev) / 2.0

    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "search": {
            "best_gain": best["gain"],
            "best_harmonic": best["harmonic"]
        },
        "refined_phases": best["phases"],
        "refined_deltas": best["deltas"],
        "RCI_fine": RCI_fine,
        "TSI_prev": TSI_prev,
        "UCI": UCI
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=4)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Constant", "Refined_Phase(rad)", "Refined_Δφ(rad)"])
        for k in best["phases"].keys():
            w.writerow([k, best["phases"][k], best["deltas"][k]])
        w.writerow(["RCI_fine(%)", RCI_fine])
        w.writerow(["Unified_Coherence_Index(%)", UCI])

    radar_plot(best["phases"], RCI_fine)
    persist(result)

    print(f"✅ Fine-Lock complete. RCI₍fine₎ = {RCI_fine:.3f} %, UCI = {UCI:.3f} %")
    print(f"   ↳ gain = {best['gain']:.3f}, harmonic = {best['harmonic']:.3f}")

    if RCI_fine > 95 and UCI > 85:
        print("🎯 Tessaris temporal coherence layer fully stabilized.")
    elif RCI_fine > 80:
        print("⚠️ Near full coherence — residual phase drift negligible.")
    else:
        print("🚨 Fine-lock incomplete — review H′4 harmonics or phase scaling.")

if __name__ == "__main__":
    main()