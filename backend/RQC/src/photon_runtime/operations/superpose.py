"""
Tessaris RQC - Photonic Runtime Operator ⊕ (superpose)
────────────────────────────────────────────────────────
Combines two symbolic-photonic waveforms into a coherent
superposed state. Provides phase-normalized amplitude mix and
coherence metric suitable for telemetry and visualization.

Input:
    Φ : np.ndarray | float
    ψ : np.ndarray | float
    meta : dict     # optional operator metadata

Output:
    dict{
        "state": np.ndarray,           # resulting field
        "Φ_mean": float,
        "ψ_mean": float,
        "resonance_index": float,
        "coherence_energy": float,
        "timestamp": float,
    }
"""

import time
from typing import Union, Dict, Any

import numpy as np


def superpose(
    phi: Union[np.ndarray, float],
    psi: Union[np.ndarray, float],
    meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Core ⊕ operation (superposition kernel)."""
    meta = meta or {}

    # Normalize inputs to arrays
    phi_arr = np.atleast_1d(phi).astype(np.complex128)
    psi_arr = np.atleast_1d(psi).astype(np.complex128)

    # Normalize amplitude scales
    phi_norm = phi_arr / (np.abs(phi_arr).max() + 1e-12)
    psi_norm = psi_arr / (np.abs(psi_arr).max() + 1e-12)

    # Core superposition - phase-preserving weighted sum
    result = (phi_norm + psi_norm) / 2.0

    # Coherence / resonance metrics
    phi_mean = float(np.mean(np.abs(phi_norm)))
    psi_mean = float(np.mean(np.abs(psi_norm)))
    coherence_energy = float(np.mean(np.abs(result) ** 2))

    # Correlation as resonance index (phase-alignment)
    denom = (np.linalg.norm(phi_norm) * np.linalg.norm(psi_norm) + 1e-12)
    resonance_index = float(np.abs(np.vdot(phi_norm, psi_norm)) / denom)

    payload: Dict[str, Any] = {
        "state": result,
        "Φ_mean": phi_mean,
        "ψ_mean": psi_mean,
        "resonance_index": resonance_index,
        "coherence_energy": coherence_energy,
        "timestamp": time.time(),
    }

    # Push metrics to CodexMetrics + MorphicLedger (via resonance_bridge.publish_metrics)
    # IMPORTANT: don't send numpy arrays to telemetry/ledger.
    try:
        from backend.RQC.src.photon_runtime.telemetry.resonance_bridge import publish_metrics

        publish_metrics("⊕", {
            "Φ_mean": payload["Φ_mean"],
            "ψ_mean": payload["ψ_mean"],
            "resonance_index": payload["resonance_index"],
            "coherence_energy": payload["coherence_energy"],
            "timestamp": payload["timestamp"],
            # optional awareness fields if you ever add them:
            # "gain": meta.get("gain"),
            # "closure_state": meta.get("closure_state"),
            # "phi_dot": meta.get("phi_dot"),
        })
    except Exception as e:
        print(f"[⊕] Telemetry publish failed: {e}")

    return payload


if __name__ == "__main__":
    φ = np.exp(1j * np.linspace(0, np.pi, 100))
    ψ = np.exp(1j * np.linspace(0, np.pi, 100) + 0.1j)
    out = superpose(φ, ψ)
    print("[⊕] Superpose metrics:")
    for k, v in out.items():
        if k != "state":
            print(f"  {k}: {v}")