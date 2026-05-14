from __future__ import annotations

from typing import Any, Mapping
import numpy as np

from .ops import (
    laplacian_periodic,
    l2_norm,
    entropy_proxy_from_psi,
    coherence_proxy,
    phase_lock_step,
)

def simulate_thermo(
    *,
    test_id: str,
    config: Mapping[str, Any],
    controller,
) -> dict[str, Any]:
    """
    2D complex lattice with Langevin-style noise injection.

    X01 goal (audit-safe): under fixed noise level ("temperature" proxy),
    a closed-loop phase-lock "recycler" reduces entropy proxy S and increases
    coherence proxy R vs baselines.

    This is a model-only proxy experiment, not real thermodynamics.
    """
    seed = int(config["seed"])
    rng = np.random.default_rng(seed)

    H = int(config["H"]); W = int(config["W"])
    steps = int(config["steps"])
    dt = float(config["dt"])

    # Protocol labels (kept for audit continuity; not used as physical constants)
    hbar = float(config.get("hbar", 1e-3))
    G = float(config.get("G", 1e-5))
    Lambda0 = float(config.get("Lambda0", 1e-6))
    alpha = float(config.get("alpha", 0.5))

    # Base dynamics (stable, audit-safe)
    nu = float(config["nu"])
    damp = float(config["damp"])

    # Noise injection ("temperature" proxy)
    T = float(config["T"])
    noise_sigma = float(config["noise_sigma"])  # independent knob (lets you scale)
    sigma = float(np.sqrt(max(T, 0.0)) * noise_sigma)  # effective noise amplitude per step

    # Init: high-noise phase field + small coherent seed
    psi = (rng.normal(0.0, 1.0, size=(H, W)) + 1j * rng.normal(0.0, 1.0, size=(H, W))).astype(np.complex128)
    psi *= 0.5
    psi[H // 2, W // 2] += 1.0 + 0.0j

    # Normalize initial energy so norm_series doesn't start huge (audit bound)
    norm0_target = float(config.get("norm0_target", 10.0))
    n0 = l2_norm(psi)
    if n0 > 1e-12:
        psi *= (norm0_target / n0)

    controller.reset()

    S_series: list[float] = []
    R_series: list[float] = []
    g_series: list[float] = []
    norm_series: list[float] = []

    for t in range(steps):
        S = entropy_proxy_from_psi(psi)
        R = coherence_proxy(psi)

        g = float(controller.step(S=S, R=R, t=t, rng=rng))

        S_series.append(float(S))
        R_series.append(float(R))
        g_series.append(float(g))
        norm_series.append(l2_norm(psi))

        # Base evolution
        lap = laplacian_periodic(psi)
        psi = psi + dt * (nu * lap - damp * psi)

        # Langevin-style noise (complex)
        noise = (rng.normal(0.0, 1.0, size=(H, W)) + 1j * rng.normal(0.0, 1.0, size=(H, W))).astype(np.complex128)
        psi = psi + dt * sigma * noise

        # Recycler action: phase-lock steering
        if g > 0.0:
            phase_lock_step(psi, gain=g, dt=dt)

        # --- Hard boundedness clamp (audit-safe) ---
        norm_cap = float(config.get("norm_cap", 20.0))
        n = l2_norm(psi)
        if n > norm_cap:
            psi *= ((norm_cap - 1e-12) / n)

    out = {
        "test_id": test_id,
        "controller": getattr(controller, "name", type(controller).__name__),
        "run_hash": None,  # filled by artifact writer
        "config": dict(config),
        "protocol": {"hbar": hbar, "G": G, "Lambda0": Lambda0, "alpha": alpha},
        "T": T,
        "noise_sigma": noise_sigma,
        "S_initial": float(S_series[0]),
        "S_final": float(S_series[-1]),
        "R_initial": float(R_series[0]),
        "R_final": float(R_series[-1]),
        "S_series": S_series,
        "R_series": R_series,
        "g_series": g_series,
        "norm_series": norm_series,
    }
    return out
