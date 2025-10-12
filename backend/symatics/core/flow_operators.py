# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.7 — Symbolic Flow Operators
# Core divergence, curl, and Laplacian operators for λ–ψ dynamics
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v0.7.0 — October 2025
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
import numpy as np
from typing import Union

try:
    from backend.modules.codex.codex_trace import record_event
except ImportError:
    def record_event(event_type: str, **fields):
        return None


Array = Union[np.ndarray, float]

# ──────────────────────────────────────────────────────────────
def divergence(field: Array) -> np.ndarray:
    """
    ∇·field — symbolic divergence operator.
    Works for 1D, 2D, or ND arrays.
    """
    if np.ndim(field) == 1:
        # Simple 1D derivative
        div = np.gradient(field)
    else:
        grads = np.gradient(field)
        if isinstance(grads, list):
            div = np.zeros_like(field)
            for i, g in enumerate(grads):
                div += np.gradient(field, axis=i)
        else:
            div = grads
    try:
        record_event("divergence", mean=float(np.mean(div)))
    except Exception:
        pass
    return div


# ──────────────────────────────────────────────────────────────
def curl(field: Array) -> np.ndarray:
    """
    ∇×field — symbolic curl operator (2D+ only).
    For 1D arrays, returns zero array.
    """
    if np.ndim(field) < 2:
        return np.zeros_like(field)

    gy, gx = np.gradient(field)
    curl_val = gy - gx

    try:
        record_event("curl", mean=float(np.mean(curl_val)))
    except Exception:
        pass
    return curl_val


# ──────────────────────────────────────────────────────────────
def laplacian(field: Array) -> np.ndarray:
    """
    ∇²ψ — discrete Laplacian operator.
    Compatible with arbitrary-dimensional grids.
    """
    grads = np.gradient(field)
    if not isinstance(grads, list):
        grads = [grads]

    lap = np.zeros_like(field)
    for g in grads:
        g2 = np.gradient(g)
        if isinstance(g2, list):
            lap += sum(g2)
        else:
            lap += g2

    try:
        record_event("laplacian", mean=float(np.mean(lap)))
    except Exception:
        pass
    return lap


# ──────────────────────────────────────────────────────────────
def coherence_flux(ψ: np.ndarray) -> np.ndarray:
    """
    Compute coherence flux Φ = e^{-||∇ψ||} * ψ.
    Used as symbolic stability metric.
    """
    grads = np.gradient(ψ)
    norm = 0.0
    if isinstance(grads, list):
        for g in grads:
            norm += g**2
        norm = np.sqrt(norm)
    else:
        norm = np.abs(grads)

    flux = np.exp(-norm) * ψ

    try:
        record_event("coherence_flux", mean=float(np.mean(flux)))
    except Exception:
        pass
    return flux


# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Minimal self-test
    x = np.linspace(0, np.pi, 64)
    ψ = np.sin(x)
    print("div:", np.mean(divergence(ψ)))
    print("lap:", np.mean(laplacian(ψ)))
    print("flux:", np.mean(coherence_flux(ψ)))