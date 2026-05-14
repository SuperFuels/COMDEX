# backend/photon_algebra/tests/paev_test_N18_memory_retention.py
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timezone

from backend.photon_algebra.utils.load_constants import load_constants

def normalize(v):
    n = np.linalg.norm(v)
    return v if n == 0 else v / n

def main():
    const = load_constants()
    ħ, G, Λ, α, β = const["ħ"], const["G"], const["Λ"], const["α"], const["β"]

    print("=== N18 - Quantum Memory Retention ===")
    print(f"ħ={ħ:.3e}, G={G:.1e}, Λ={Λ:.1e}, α={α:.3f}, β={β:.2f}")

    # Spatial grid (1D profile) and initial encoded state
    x = np.linspace(-5, 5, 200)
    psi0 = np.exp(-x**2) * (1 + 0.15*np.cos(2.0*x))          # a bit of structure
    psi0 = normalize(psi0.astype(np.complex128))

    # Iterative "cycle" map: phase kick + gentle diffusion (decoherence proxy)
    cycles = 24
    omega = 0.5                       # base phase rate
    gamma = 0.06                      # diffusion strength (memory loss proxy)
    phase_gain = 1.0                  # scale of phase kick per cycle

    fidelities = []
    states = [psi0.copy()]
    psi = psi0.copy()

    for k in range(1, cycles+1):
        # Phase kick (ER=EPR-like feedback; β modulates nonlinearity)
        phase = phase_gain * (omega*k + β*np.sin(k*0.7))
        psi *= np.exp(1j * phase)

        # Gentle diffusion (loss) via discrete Laplacian
        lap = np.roll(psi, 1) - 2*psi + np.roll(psi, -1)
        psi = psi + gamma * lap

        # Normalize to isolate coherence loss from amplitude drift
        psi = normalize(psi)

        # Fidelity to original encoding
        F = np.abs(np.vdot(psi0, psi)) / (np.linalg.norm(psi0)*np.linalg.norm(psi))
        fidelities.append(float(F))
        states.append(psi.copy())

    fidelities = np.array(fidelities)

    # Memory half-life (cycles to drop below ~0.707 ≈ sqrt(0.5)) and 0.90 thresholds
    def first_below(arr, thr):
        idx = np.where(arr < thr)[0]
        return int(idx[0]) + 1 if idx.size > 0 else None

    half_life = first_below(fidelities, 0.707)
    life_90 = first_below(fidelities, 0.90)

    classification = (
        "✅ Long-lived"
        if (half_life is None or half_life > cycles)
        else ("⚠️ Moderate retention" if (half_life and half_life >= cycles//2) else "❌ Short-lived")
    )

    print(f"Half-life (<=0.707 fidelity): {half_life if half_life is not None else '>= %d'%cycles}")
    print(f"90% retention limit: {life_90 if life_90 is not None else '>= %d'%cycles}")
    print(f"Final fidelity: {fidelities[-1]:.3f}")
    print(f"Classification: {classification}")

    # Plots
    plt.figure(figsize=(8,5))
    plt.plot(range(1, cycles+1), fidelities, marker='o', lw=1)
    plt.axhline(0.90, ls='--', alpha=0.5)
    plt.axhline(0.707, ls='--', alpha=0.5)
    plt.xlabel("Cycle")
    plt.ylabel("Fidelity to initial state")
    plt.title("N18: Memory Retention (Cycle Fidelity)")
    plt.grid(True)
    plt.savefig("PAEV_N18_FidelityDecay.png", bbox_inches="tight")

    plt.figure(figsize=(8,5))
    plt.plot(x, np.real(psi0), label="Initial ψ (real)")
    plt.plot(x, np.real(states[-1]), label="Final ψ (real)")
    plt.xlabel("x")
    plt.ylabel("Re[ψ]")
    plt.title("N18: Initial vs Final State (Real Part)")
    plt.legend()
    plt.grid(True)
    plt.savefig("PAEV_N18_MemoryCurve.png", bbox_inches="tight")

    # Summary -> knowledge
    summary = {
        "ħ": ħ, "G": G, "Λ": Λ, "α": α, "β": β,
        "cycles": cycles,
        "omega": omega,
        "gamma": gamma,
        "phase_gain": phase_gain,
        "fidelities": fidelities.tolist(),
        "half_life_cycles": half_life,
        "life_90_cycles": life_90,
        "final_fidelity": float(fidelities[-1]),
        "classification": classification,
        "files": {
            "fidelity_plot": "PAEV_N18_FidelityDecay.png",
            "curve_plot": "PAEV_N18_MemoryCurve.png"
        },
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    }
    out = Path("backend/modules/knowledge/N18_memory_retention.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print(f"✅ Plots saved:\n  - PAEV_N18_FidelityDecay.png\n  - PAEV_N18_MemoryCurve.png")
    print(f"📄 Summary: {out}")

if __name__ == "__main__":
    main()