from __future__ import annotations

from typing import Any, Mapping
import numpy as np

from .ops import window, corr_complex, l2_norm
from .throat import apply_throat_coupling

def simulate_connectivity(
    *,
    test_id: str,
    config: Mapping[str, Any],
    controller,
) -> dict[str, Any]:
    """
    2D complex lattice packet:
      - packet starts at source
      - diffusion-like spread (audit-safe)
      - optional throat coupling between source and dest nodes
      - arrival measured by correlation threshold in a local window
    """
    seed = int(config["seed"])
    rng = np.random.default_rng(seed)

    H = int(config["H"]); W = int(config["W"])
    steps = int(config["steps"])
    dt = float(config["dt"])

    # Protocol constants (pinned by spec; used as config labels here)
    hbar = float(config.get("hbar", 1e-3))
    G = float(config.get("G", 1e-5))
    Lambda0 = float(config.get("Lambda0", 1e-6))
    alpha = float(config.get("alpha", 0.5))

    # Throat knobs
    eta = float(config["eta"])                 # conductance
    a = tuple(config["src_xy"])                # (x,y)
    b = tuple(config["dst_xy"])                # (x,y)
    corr_r = int(config["corr_window_r"])
    C_thresh = float(config["C_thresh"])

    # Mild diffusion + damping (audit-safe, stable)
    nu = float(config["nu"])
    damp = float(config["damp"])

    psi = np.zeros((H, W), dtype=np.complex128)
    x0, y0 = a
    psi[y0, x0] = 1.0 + 0.0j  # localized injection

    controller.reset()

    C_series: list[float] = []
    sigma_series: list[float] = []
    norm_series: list[float] = []

    arrival_step: int | None = None

    for t in range(steps):
        # Observe correlation
        src_w = window(psi, x0, y0, r=corr_r)
        x1, y1 = b
        dst_w = window(psi, x1, y1, r=corr_r)
        C = corr_complex(dst_w, src_w)

        sigma = float(controller.step(C=C, t=t, rng=rng))
        sigma_series.append(sigma)
        C_series.append(C)
        norm_series.append(l2_norm(psi))

        if arrival_step is None and C >= C_thresh:
            arrival_step = t

        # Diffusion-like update (periodic)
        lap = (
            np.roll(psi, 1, axis=0) + np.roll(psi, -1, axis=0) +
            np.roll(psi, 1, axis=1) + np.roll(psi, -1, axis=1) -
            4.0 * psi
        )
        psi = psi + dt * (nu * lap - damp * psi)

        # Apply throat coupling AFTER base dynamics
        if sigma > 0.0:
            apply_throat_coupling(psi, a=a, b=b, eta=eta, sigma=sigma, dt=dt)

        # Tiny phase noise (deterministic seed) to prevent trivial artifacts
        psi *= np.exp(1j * (0.0 + 1e-6 * rng.normal()))

    if arrival_step is None:
        arrival_step = steps  # "did not arrive"

    out = {
        "test_id": test_id,
        "controller": getattr(controller, "name", type(controller).__name__),
        "run_hash": None,  # filled by artifact writer
        "config": dict(config),
        "eta": eta,
        "C_thresh": C_thresh,
        "arrival_step": int(arrival_step),
        "C_final": float(C_series[-1]),
        "C_series": C_series,
        "sigma_series": sigma_series,
        "norm_series": norm_series,
        "protocol": {"hbar": hbar, "G": G, "Lambda0": Lambda0, "alpha": alpha},
    }
    return out
