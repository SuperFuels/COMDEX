from __future__ import annotations

import numpy as np

EPS = 1e-12

def entropy_proxy_from_psi(psi: np.ndarray) -> float:
    """
    Shannon entropy of the normalized intensity distribution p = |psi|^2.
    This should be >0 for any spread-out/noisy state.
    """
    p = np.abs(psi) ** 2
    s = float(np.sum(p))
    if s <= EPS:
        return 0.0
    q = p / s
    return float(-np.sum(q * np.log(q + EPS)))

def clip(x: float, lo: float, hi: float) -> float:
    return float(np.clip(x, lo, hi))

def l2_norm(a: np.ndarray) -> float:
    return float(np.sqrt(np.sum(np.abs(a) ** 2) + EPS))

def laplacian_periodic(psi: np.ndarray) -> np.ndarray:
    return (
        np.roll(psi, 1, axis=0) + np.roll(psi, -1, axis=0) +
        np.roll(psi, 1, axis=1) + np.roll(psi, -1, axis=1) -
        4.0 * psi
    )

def coherence_proxy(psi: np.ndarray) -> float:
    """
    Coherence proxy R_sync in [0,1]:
      R = |mean(psi)| / mean(|psi|)
    ~1 => phase-aligned; ~0 => random phases / cancellation.
    """
    denom = float(np.mean(np.abs(psi)) + EPS)
    num = float(np.abs(np.mean(psi)))
    return float(np.clip(num / denom, 0.0, 1.0))

def entropy_proxy(psi: np.ndarray) -> float:
    """
    Entropy-like proxy S >= 0:
      combine amplitude dispersion + phase dispersion.
    This is NOT physical thermodynamic entropy; it's an audit-safe scalar proxy.
    """
    amp = np.abs(psi)
    amp_var = float(np.var(amp))
    phase = np.angle(psi)
    # phase circular dispersion proxy: 1 - |mean(e^{i phase})|
    circ = 1.0 - float(np.abs(np.mean(np.exp(1j * phase))))
    # log keeps scale reasonable
    S = float(np.log(EPS + amp_var + 0.25 * circ))
    return float(max(S, 0.0))

def phase_lock_step(psi: np.ndarray, *, gain: float, dt: float) -> None:
    """
    Phase-lock steering: rotate phases toward the global mean phase.
    gain in [0,1]. In-place update.
    """
    if gain <= 0.0:
        return
    mu = np.mean(psi)
    if np.abs(mu) < 1e-10:
        return
    theta = np.angle(mu)
    # Pull phases toward theta using a small rotation.
    psi *= np.exp(-1j * gain * dt * (np.angle(psi) - theta))

# --- X01 entropy wiring (force phase-entropy) ---
# If older entropy_proxy() exists above, this override ensures the simulator uses
# the phase-disorder entropy (what the recycler actually targets).

def entropy_proxy(psi: np.ndarray) -> float:
    return entropy_proxy_from_psi(psi)

# --- X01: phase-disorder entropy proxy (override at EOF) ---
# Uses existing coherence_proxy(psi) (phase alignment). Entropy is "disorder":
#   S = 1 - R_phase
def entropy_proxy_from_psi(psi: np.ndarray) -> float:
    R = coherence_proxy(psi)
    return float(max(0.0, min(1.0, 1.0 - R)))

# Back-compat: anything still calling entropy_proxy() gets the correct X01 metric
def entropy_proxy(psi: np.ndarray) -> float:
    return entropy_proxy_from_psi(psi)
