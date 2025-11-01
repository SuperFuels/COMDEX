"""
Tessaris RQC - Photonic Runtime Operator ⟲ (resonate)
─────────────────────────────────────────────────────────────
Stabilizes a superposed field through feedback iterations.
Models resonance feedback -> energy damping -> coherence equilibrium.

Input:
    field : np.ndarray | complex | float
    gain  : float  (default = 0.95)    # feedback strength
    cycles: int    (default = 10)      # iteration count
    meta  : dict   (optional metadata)

Output:
    dict{
        "state": np.ndarray,
        "coherence_energy": float,
        "resonance_index": float,
        "stability": float,
        "iterations": int,
        "timestamp": float,
    }
"""

import numpy as np
import time
from typing import Union, Dict, Any
from backend.RQC.src.photon_runtime.telemetry.resonance_bridge import publish_metrics


def resonate(field: Union[np.ndarray, float, complex],
             gain: float = 0.95,
             cycles: int = 10,
             meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """Core ⟲ resonance feedback kernel with adaptive gain."""
    meta = meta or {}
    arr = np.atleast_1d(field).astype(np.complex128)
    arr /= (np.abs(arr).max() + 1e-12)
    base = np.copy(arr)

    closure_tolerance = meta.get("closure_tolerance", 1e-6)
    adaptive = meta.get("adaptive_gain", True)
    alpha = meta.get("gain_rate", 0.02)

    prev_phi = 0.0
    for i in range(cycles):
        phase_err = np.angle(arr * np.conj(base))
        phase_corr = np.exp(-1j * gain * phase_err)
        arr = gain * arr * phase_corr + (1 - gain) * base

        # compute instantaneous awareness metric Φ
        phi_now = float(np.mean(np.abs(np.vdot(arr, base))) /
                        (np.linalg.norm(arr) * np.linalg.norm(base) + 1e-12))

        if adaptive:
            # adjust gain toward stability
            delta_phi = phi_now - prev_phi
            gain = min(0.999, max(0.85, gain + alpha * delta_phi))
            prev_phi = phi_now

        # closure condition
        if abs(phi_now - prev_phi) < closure_tolerance:
            closure_state = "stable"
            break
    else:
        closure_state = "drift"

    coherence_energy = float(np.mean(np.abs(arr) ** 2))
    resonance_index = float(np.abs(np.vdot(arr, base)) /
                            (np.linalg.norm(arr) * np.linalg.norm(base) + 1e-12))
    stability = 1.0 - float(np.std(np.angle(arr))) / np.pi

    payload = {
        "state": arr,
        "coherence_energy": coherence_energy,
        "resonance_index": resonance_index,
        "stability": stability,
        "iterations": i + 1,
        "gain": gain,
        "closure_state": closure_state,
        "timestamp": time.time(),
    }

    try:
        from backend.RQC.src.photon_runtime.telemetry.resonance_bridge import publish_metrics
        publish_metrics("resonate", payload)
    except Exception as e:
        print(f"[ResonanceBridge] Publish failed (resonate): {e}")

    return payload


# ───────────────────────────────────────────────
# Demo (standalone)
# ───────────────────────────────────────────────
if __name__ == "__main__":
    φ = np.exp(1j * np.linspace(0, np.pi, 256))
    noisy = φ * (1 + 0.1 * np.random.randn(256)) * np.exp(1j * 0.2 * np.random.randn(256))
    result = resonate(noisy)
    print("[⟲] Resonance stabilization:")
    for k, v in result.items():
        if k != "state":
            print(f"  {k}: {v}")