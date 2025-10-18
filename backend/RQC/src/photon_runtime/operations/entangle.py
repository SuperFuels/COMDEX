"""
Tessaris RQC — Photonic Runtime Operator ↔ (entangle)
─────────────────────────────────────────────────────────────
Couples two symbolic–photonic fields into an entangled mode pair.
Maintains phase correlation and computes entanglement fidelity
for CodexTrace, GHX telemetry, and MorphicLedger.

Input:
    phi1 : np.ndarray | float
    phi2 : np.ndarray | float
    meta : dict (optional operator metadata)

Output:
    dict{
        "state_A": np.ndarray,
        "state_B": np.ndarray,
        "entanglement_fidelity": float,
        "mutual_coherence": float,
        "phase_correlation": float,
        "timestamp": float,
    }
"""

import numpy as np
import time
from typing import Union, Dict, Any
from backend.RQC.src.photon_runtime.telemetry.resonance_bridge import publish_metrics


def entangle(
    phi1: Union[np.ndarray, float],
    phi2: Union[np.ndarray, float],
    meta: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Core ↔ operation (mode coupling + phase lock)."""
    meta = meta or {}

    # ────────────────────────────────
    # Normalize input amplitudes
    # ────────────────────────────────
    a = np.atleast_1d(phi1).astype(np.complex128)
    b = np.atleast_1d(phi2).astype(np.complex128)
    a /= (np.abs(a).max() + 1e-12)
    b /= (np.abs(b).max() + 1e-12)

    # ────────────────────────────────
    # Create coupled, phase-locked fields
    # ────────────────────────────────
    phase_diff = np.angle(a * np.conj(b))
    coupling_strength = meta.get("coupling_strength", 0.8)
    correction = np.exp(-1j * coupling_strength * phase_diff)

    entangled_A = (a + correction * b) / 2.0
    entangled_B = (b + np.conj(correction) * a) / 2.0

    # ────────────────────────────────
    # Compute entanglement metrics
    # ────────────────────────────────
    mutual_coherence = float(np.abs(np.vdot(entangled_A, entangled_B)) /
                             (np.linalg.norm(entangled_A) * np.linalg.norm(entangled_B) + 1e-12))
    phase_correlation = float(np.mean(np.cos(np.angle(entangled_A * np.conj(entangled_B)))))
    entanglement_fidelity = (mutual_coherence + phase_correlation) / 2.0

    payload = {
        "state_A": entangled_A,
        "state_B": entangled_B,
        "entanglement_fidelity": entanglement_fidelity,
        "mutual_coherence": mutual_coherence,
        "phase_correlation": phase_correlation,
        "timestamp": time.time(),
    }

    # ────────────────────────────────
    # Publish to telemetry systems
    # ────────────────────────────────
    try:
        operator = "entangle"
        publish_metrics(operator, payload)
    except Exception as e:
        print(f"[ResonanceBridge] Publish failed ({operator}): {e}")

    return payload


# ───────────────────────────────────────────────
# Demo (standalone execution)
# ───────────────────────────────────────────────
if __name__ == "__main__":
    phi1 = np.exp(1j * np.linspace(0, np.pi, 256))
    phi2 = np.exp(1j * np.linspace(0, np.pi, 256) + 0.25j)
    result = entangle(phi1, phi2)
    print("[↔] Entanglement metrics:")
    for k, v in result.items():
        if not isinstance(v, np.ndarray):
            print(f"  {k}: {v}")