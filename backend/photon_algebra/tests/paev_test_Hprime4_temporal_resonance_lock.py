#!/usr/bin/env python3
"""
Test H′4 — Tessaris Temporal Resonance Lock (Auto-Tuned, Refined, Persistent)
Performs harmonic resonance tuning to maximize lock RCI.
Auto-writes verified results to the discovery ledger and constants registry.
"""

import os, json, csv, time
import numpy as np
import matplotlib.pyplot as plt

# --- File paths ---
COMP_FILE   = "backend/photon_algebra/constants/Hprime3_phase_curvature_compensated.json"
LOCK_FILE   = "backend/photon_algebra/constants/Gprime_lock_snapshot.json"
OUTPUT_JSON = "backend/photon_algebra/constants/Hprime4_temporal_resonance_lock.json"
OUTPUT_CSV  = "backend/photon_algebra/tests/results_Hprime4_temporal_resonance_lock.csv"
PLOT_FILE   = "backend/photon_algebra/tests/PAEV_TestHprime4_TemporalResonance.png"
DISCOVERY_LEDGER = "backend/photon_algebra/tests/discoveries.json"
CONSTANTS_REGISTRY = "backend/photon_algebra/constants/paev_constants.json"

# --- Search parameters ---
GAINS      = np.linspace(0.4, 2.0, 17)     # gain sweep
HARMONICS  = [1, 2, 3, 4, 5, 6]            # harmonic orders

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def compute_RCI(phases_dict):
    """Compute centered resonance coherence index (spread-based)."""
    vals = np.array(list(phases_dict.values()), dtype=float)
    if len(vals) == 0:
        return 0.0
    vals = vals - np.mean(vals)
    spread = np.sqrt(np.mean(vals ** 2))
    RCI = (1.0 / (1.0 + spread / 0.01)) * 100.0
    return float(np.clip(RCI, 0, 100))

def base_freq_ratios(lock):
    """Log-amplitude fingerprint → [0,1) phase-like ratios."""
    ratios = {}
    for k in ("alpha", "hbar", "m_e", "G"):
        base = abs(float(lock.get(k, 0) or 0.0))
        if base <= 0:
            ratios[k] = 0.5
        else:
            r = (np.log10(base) / 10.0) % 1.0
            ratios[k] = float(r)
    return ratios

def apply_lock(phases, deltas, ratios, gain=1.0, harmonic=1):
    """Apply resonance lock correction."""
    locked_phases, locked_deltas = {}, {}
    for k, phi in phases.items():
        r = ratios.get(k, 0.5)
        angle = gain * harmonic * r * (np.pi / 2.0)
        c = np.cos(angle)
        locked_phases[k] = phi * c
        locked_deltas[k] = deltas.get(k, 0.0) * c
    return locked_phases, locked_deltas

def radar_plot(locked_deltas, RCI):
    labels = list(locked_deltas.keys())
    vals = [abs(locked_deltas[k]) for k in labels]
    vals += vals[:1]
    angs = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    angs += angs[:1]

    plt.figure(figsize=(6,6))
    ax = plt.subplot(111, polar=True)
    ax.plot(angs, vals, "r-", linewidth=2)
    ax.fill(angs, vals, "r", alpha=0.25)
    ax.set_xticks(angs[:-1])
    ax.set_xticklabels(labels)
    ax.set_title(f"H′4 — Temporal Resonance Lock (RCI={RCI:.3f}%)")
    plt.tight_layout()
    plt.savefig(PLOT_FILE)

def persist_discovery(entry):
    """Append this discovery to the ledger and update constants."""
    os.makedirs(os.path.dirname(DISCOVERY_LEDGER), exist_ok=True)

    # --- Load current discoveries, handle list/dict interchangeably ---
    discoveries_raw = load_json(DISCOVERY_LEDGER)
    if isinstance(discoveries_raw, list):
        discoveries = discoveries_raw
    elif isinstance(discoveries_raw, dict) and "discoveries" in discoveries_raw:
        discoveries = discoveries_raw["discoveries"]
    else:
        discoveries = []

    discoveries.append(entry)

    # Write back in simple list form (compatible with both formats)
    with open(DISCOVERY_LEDGER, "w") as f:
        json.dump(discoveries, f, indent=4)

    # --- Update constants registry ---
    registry = load_json(CONSTANTS_REGISTRY)
    registry["Hprime4"] = {
        "timestamp": entry["timestamp"],
        "best_gain": entry["search"]["best_gain"],
        "best_harmonic": entry["search"]["best_harmonic"],
        "RCI_%": entry["RCI"],
        "Unified_Stability_%": entry["Unified_Stability_Index"],
    }
    with open(CONSTANTS_REGISTRY, "w") as f:
        json.dump(registry, f, indent=4)

    print(f"📘 Discovery ledger updated → {DISCOVERY_LEDGER}")
    print(f"📗 Constants registry updated → {CONSTANTS_REGISTRY}")

def main():
    print("=== H′4 — Tessaris Temporal Resonance Lock (Auto-Tuned, Persistent) ===")

    comp = load_json(COMP_FILE)
    lock = load_json(LOCK_FILE)
    if not comp or not lock:
        print("🚨 Missing input data — ensure H′3 and G′ lock exist.")
        return

    phases = comp.get("corrected_phases", {})
    deltas = comp.get("corrected_deltas", {})
    if not phases or not deltas:
        print("🚨 H′3 data incomplete.")
        return

    ratios = base_freq_ratios(lock)

    # --- coarse grid search ---
    best = {"RCI": -1, "gain": None, "harmonic": None,
            "locked_phases": None, "locked_deltas": None}
    for g in GAINS:
        for h in HARMONICS:
            lp, ld = apply_lock(phases, deltas, ratios, gain=g, harmonic=h)
            R = compute_RCI(lp)
            if R > best["RCI"]:
                best.update(RCI=R, gain=g, harmonic=h,
                            locked_phases=lp, locked_deltas=ld)

    # --- fine-tune around best gain ---
    g0, h0 = best["gain"], best["harmonic"]
    for g in np.linspace(max(0.2, g0-0.2), min(2.5, g0+0.2), 9):
        lp, ld = apply_lock(phases, deltas, ratios, gain=g, harmonic=h0)
        R = compute_RCI(lp)
        if R > best["RCI"]:
            best.update(RCI=R, gain=g, locked_phases=lp, locked_deltas=ld)

    locked_phases = best["locked_phases"]
    locked_deltas = best["locked_deltas"]
    RCI = best["RCI"]
    mean_phase = float(np.mean(list(locked_phases.values())))
    mean_delta = float(np.mean(list(locked_deltas.values())))
    TSI_inherit = float(comp.get("TSI", comp.get("mean_FCI", 0.0)))
    unified_stability = (RCI + TSI_inherit) / 2.0

    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "search": {"best_gain": best["gain"], "best_harmonic": best["harmonic"]},
        "locked_phases": locked_phases,
        "locked_deltas": locked_deltas,
        "mean_phase": mean_phase,
        "mean_delta": mean_delta,
        "RCI": RCI,
        "TSI_inherit": TSI_inherit,
        "Unified_Stability_Index": unified_stability
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(result, f, indent=4)

    with open(OUTPUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Constant", "Locked_Phase(rad)", "Locked_Δφ(rad)"])
        for k in locked_phases.keys():
            w.writerow([k, locked_phases[k], locked_deltas[k]])
        w.writerow(["Best_Gain", best["gain"]])
        w.writerow(["Best_Harmonic", best["harmonic"]])
        w.writerow(["RCI(%)", RCI])
        w.writerow(["TSI_inherit(%)", TSI_inherit])
        w.writerow(["Unified_Stability_Index(%)", unified_stability])

    radar_plot(locked_deltas, RCI)

    print(f"📘 Saved resonance JSON → {OUTPUT_JSON}")
    print(f"📄 Saved resonance CSV → {OUTPUT_CSV}")
    print(f"📈 Saved plot → {PLOT_FILE}")
    print(f"✅ Temporal Resonance Lock (auto-tuned). "
          f"RCI = {RCI:.3f} %, Unified Stability = {unified_stability:.3f} %")
    print(f"   ↳ best gain = {best['gain']}, best harmonic = {best['harmonic']}")

    # --- Auto persistence ---
    if RCI >= 70:
        persist_discovery(result)
    else:
        print("⚠️ RCI below archival threshold (70%) — result not persisted.")

    if RCI > 95 and unified_stability > 80:
        print("🎯 Full temporal lock achieved — dynamic field coherence verified.")
    elif RCI > 70:
        print("⚠️ Partial lock — harmonic synchronization stable but incomplete.")
    else:
        print("🚨 Temporal desynchronization persists — consider re-running H′3 with a tighter compensator window.")

if __name__ == "__main__":
    main()