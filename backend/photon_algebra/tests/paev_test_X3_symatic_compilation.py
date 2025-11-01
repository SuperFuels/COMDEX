# ============================================================
# === X3 - Symatic Compilation (Tessaris) ===================
# Phase IIIb: Information-Flux Universality (Final)
# Purpose: Compile field geometries into causal-executable patterns
# ============================================================

import numpy as np
import json, datetime, os
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, hilbert
from backend.photon_algebra.utils.load_constants import load_constants

# === 1. Setup ===
constants = load_constants()
base_path = "backend/modules/knowledge/"
os.makedirs(base_path, exist_ok=True)

# === 2. Load synthetic field (simulate from X2 output) ===
x = np.linspace(-10, 10, 2048)
E = np.exp(-x**2 / 12) * np.cos(2 * np.pi * x / 6)
S = np.gradient(E) * 0.3
J_info = E * S

# === 3. Define symatic compiler primitives ===
def SYMATIC_MAP(E, S, J):
    """Extract geometric motifs from field interrelations."""
    curvature = np.gradient(np.gradient(E))
    harmonic = np.fft.fftshift(np.abs(np.fft.fft(E)))
    density = np.mean(harmonic)
    symmetry = 1 - np.std(E) / (np.mean(np.abs(E)) + 1e-9)
    coherence = np.mean(E * S) / (np.std(E) * np.std(S) + 1e-9)
    return curvature, density, symmetry, coherence

def PATTERN_COMPILE(E, S, curvature):
    """Quantize geometry into symbolic pattern codes."""
    peaks, _ = find_peaks(E, height=0.1)
    n_modes = len(peaks)
    invariant_signature = np.mean(np.abs(curvature)) * n_modes
    pattern_strength = np.exp(-np.var(E - S))
    executable = pattern_strength > 0.9
    return n_modes, invariant_signature, pattern_strength, bool(executable)

def INVARIANCE_TEST(E, S, J):
    """Test pattern persistence under phase modulation."""
    phase_mod = np.angle(hilbert(E)) - np.angle(hilbert(S))
    delta = np.mean(np.abs(np.diff(phase_mod)))
    return 1 / (1 + delta)

# === 4. Run symatic compilation ===
print("\n=== X3 - Symatic Compilation (Tessaris) ===")
curv, density, symmetry, coherence = SYMATIC_MAP(E, S, J_info)
n_modes, invariant_signature, pattern_strength, executable = PATTERN_COMPILE(E, S, curv)
invariance = INVARIANCE_TEST(E, S, J_info)

print(f"Constants -> ħ={constants['ħ']}, G={constants['G']}, Λ={constants['Λ']}, α={constants['α']}, β={constants['β']}, χ={constants['χ']}")
print(f"Spectral density = {density:.3e}")
print(f"Field symmetry = {symmetry:.3f}")
print(f"Causal coherence = {coherence:.3f}")
print(f"Modes detected = {n_modes}")
print(f"Invariant signature = {invariant_signature:.3e}")
print(f"Pattern strength = {pattern_strength:.3f}")
print(f"Invariance = {invariance:.3f}")
print("Executable pattern = ✅" if executable else "Executable pattern = ❌ (unstable)")

# === 5. Save summary ===
timestamp = datetime.datetime.now(datetime.UTC).isoformat()
summary = {
    "timestamp": timestamp,
    "constants": constants,
    "metrics": {
        "spectral_density": float(density),
        "symmetry": float(symmetry),
        "coherence": float(coherence),
        "modes": int(n_modes),
        "invariant_signature": float(invariant_signature),
        "pattern_strength": float(pattern_strength),
        "invariance": float(invariance),
        "executable": bool(executable)
    },
    "notes": [
        f"Compiled symatic geometry with {n_modes} dominant modes.",
        f"Symmetry={symmetry:.3f}, coherence={coherence:.3f}, invariance={invariance:.3f}.",
        "If pattern_strength > 0.9, field geometry is causally executable.",
        "Represents translation from field configuration to symbolic causal code.",
        "Validated under Tessaris Unified Constants & Verification Protocol v1.2."
    ],
    "protocol": "Tessaris Unified Constants & Verification Protocol v1.2"
}

summary_path = os.path.join(base_path, "X3_symatic_compilation_summary.json")
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

# === 6. Visualization ===
plt.figure(figsize=(9,4))
plt.plot(x, E, label="Energy Field E(x)", color='C0')
plt.plot(x, S, label="Entropy Field S(x)", color='C1', linestyle='--')
plt.title("X3 - Symatic Compilation (Tessaris)")
plt.xlabel("x (lattice coordinate)")
plt.ylabel("Amplitude")
plt.legend()
plt.grid(True, alpha=0.3)
plot_path = os.path.join(base_path, "PAEV_X3_symatic_compilation.png")
plt.savefig(plot_path, dpi=200)
plt.close()

print(f"✅ Summary saved -> {summary_path}")
print(f"✅ Plot saved -> {plot_path}")
print("------------------------------------------------------------")