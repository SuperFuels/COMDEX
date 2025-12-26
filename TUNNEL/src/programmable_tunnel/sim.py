from __future__ import annotations

from typing import Any, Dict, Mapping

import numpy as np

from .ops import gaussian_wavepacket, kgrid_1d


def _absorber_mask(n: int, strength: float = 0.02, width_frac: float = 0.08) -> np.ndarray:
    """Simple deterministic absorber near boundaries to prevent wrap reflections.

    Mask is 1 in the center, decays to (1-strength) at edges.
    """
    w = max(2, int(width_frac * n))
    mask = np.ones(n, dtype=float)
    # left edge
    for i in range(w):
        r = (w - i) / w
        mask[i] *= np.exp(-strength * r * r)
    # right edge
    for i in range(n - w, n):
        r = (i - (n - w)) / w
        mask[i] *= np.exp(-strength * r * r)
    return mask


def simulate_tunnel(
    *,
    test_id: str,
    config: Mapping[str, Any],
    controller,
    T_target: float,
) -> Dict[str, Any]:
    """1D tunneling proxy: split-step spectral propagator with controllable barrier.

    State: complex wavefunction psi(x)

    Barrier: V(x) = V0 on a window [b0, b1)

    Observable:
      - Transmission T(t): probability mass to the right of barrier.

    Control knob:
      - V0(t): barrier height, bounded.

    Audit-safe claims:
      - Programmable barrier transmission in a controlled lattice model.
      - No physical-world tunneling claims.
    """

    seed = int(config.get("seed", 1337))
    rng = np.random.default_rng(seed)

    n = int(config.get("n", 512))
    steps = int(config.get("steps", 1200))
    dt = float(config.get("dt", 0.002))
    dx = float(config.get("dx", 1.0))

    # packet (support both generic keys and the TN01-named keys)
    x0 = float(config.get("packet_x0", config.get("x0", 0.20)))  # fraction of domain
    sigma = float(config.get("packet_sigma", config.get("sigma", 12.0)))
    k0 = float(config.get("packet_k0", config.get("k0", 0.35)))

    # barrier (support both v0 and v0_0)
    v0_0 = float(config.get("v0", config.get("v0_0", 4.0)))
    v0_min = float(config.get("v0_min", 0.0))
    v0_max = float(config.get("v0_max", 8.0))
    b_center = float(config.get("barrier_center", 0.55))  # fraction
    bw_frac = float(config.get("barrier_width_frac", 0.0))
    if bw_frac > 0.0:
        b_width = max(2, int(round(bw_frac * n)))
    else:
        b_width = int(config.get("barrier_width", 28))

    # absorber
    abs_strength = float(config.get("absorber_strength", 0.03))
    abs_width_frac = float(config.get("absorber_width_frac", 0.08))

    # domain
    x = np.arange(n, dtype=float) * dx

    # initial packet on left
    psi = gaussian_wavepacket(
        x=x,
        x0=x0 * (n * dx),
        sigma=sigma,
        k0=k0,
    )

    # spectral grid
    kk = kgrid_1d(n, dx)
    nu = float(config.get("nu", 1.0))
    kinetic_phase = np.exp(-1j * dt * nu * (kk * kk))

    absorber = _absorber_mask(n, strength=abs_strength, width_frac=abs_width_frac)

    # barrier indices
    bc = int(b_center * n)
    b0 = int(np.clip(bc - b_width // 2, 0, n - 1))
    b1 = int(np.clip(bc + b_width // 2, 0, n))

    # measurement region: either explicit fraction, or safely right of barrier.
    mrof = config.get("measure_right_of", None)
    if mrof is not None:
        right0 = int(np.clip(float(mrof) * n, 0, n))
    else:
        right0 = min(n, b1 + int(0.08 * n))  # sufficiently right of barrier

    # series
    t_series: list[float] = []
    v0_series: list[float] = []
    T_series: list[float] = []
    coh_series: list[float] = []
    norm_series: list[float] = []

    v0 = float(v0_0)
    v0_initial = float(v0_0)

    for t in range(steps):
        # build potential
        V = np.zeros(n, dtype=float)
        V[b0:b1] = v0

        # propagate one step (split-step)
        psi = np.fft.ifft(np.fft.fft(psi) * kinetic_phase)
        psi = psi * np.exp(-1j * dt * V)
        psi = psi * absorber

        # observables
        prob = np.abs(psi) ** 2
        Z = float(prob.sum()) + 1e-30
        prob /= Z

        T = float(prob[right0:].sum())

        # coherence proxy of the transmitted region (phase-lock score in [0,1])
        psi_r = psi[right0:]
        denom = float(np.sum(np.abs(psi_r))) + 1e-30
        coh = float(np.abs(np.sum(psi_r)) / denom)

        # (non-unitary absorber exists) keep a cheap norm diagnostic
        norm = float(np.sum(np.abs(psi) ** 2))

        # controller updates barrier height for next step
        if controller is not None:
            v0 = float(
                controller.step(
                    v0=v0,
                    t=t,
                    t_steps=steps,
                    T=T,
                    T_target=float(T_target),
                    rng=rng,
                )
            )
        v0 = float(np.clip(v0, v0_min, v0_max))

        t_series.append(float(t * dt))
        v0_series.append(float(v0))
        T_series.append(float(T))
        coh_series.append(float(coh))
        norm_series.append(float(norm))

    run = dict(
        test_id=test_id,
        config=dict(config),
        T_target=float(T_target),
        T_final=float(T_series[-1]),
        T_err_final=float(abs(T_series[-1] - float(T_target))),
        coh_final=float(coh_series[-1]),
        norm_final=float(norm_series[-1]),
        v0_initial=float(v0_initial),
        v0_final=float(v0_series[-1]),
        t_series=t_series,
        v0_series=v0_series,
        T_series=T_series,
        coh_series=coh_series,
        norm_series=norm_series,
        barrier=dict(b0=int(b0), b1=int(b1), right0=int(right0)),
    )
    return run
