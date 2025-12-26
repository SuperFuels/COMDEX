from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import numpy as np


@dataclass(frozen=True)
class MT01Config:
    n: int = 256
    steps: int = 5000

    alpha: float = 0.06
    lam: float = 0.002
    noise_std: float = 0.002

    amp0: float = 1.0
    sigma0: float = 6.0

    chi_base: float = 0.008
    clip: float = 6.0

    # Back-compat (some callers may pass dt even if unused)
    dt: float = 1.0


def config_to_dict(cfg: MT01Config) -> dict:
    return asdict(cfg)


def _run_hash(test_id: str, cfg: MT01Config, controller_name: str, seed: int) -> str:
    payload = {
        "test_id": test_id,
        "cfg": config_to_dict(cfg),
        "controller": controller_name,
        "seed": seed,
    }
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:7]


def run_mt01(cfg: MT01Config, controller, *, seed: int = 1337, write_artifacts: bool = True) -> dict:
    """
    MT01: Soliton Persistence (model-only).
    Proxy dynamics + artifact emission.

    Key design choice:
      - High gain increases effective noise + adds mild dissipative loss.
      - This makes random jitter worse than a bounded controller.
    """
    test_id = "MT01"
    rng = np.random.default_rng(seed)

    if hasattr(controller, "reset"):
        controller.reset(seed)

    peak0 = float(cfg.amp0)
    width0 = float(cfg.sigma0)

    peak = peak0
    width = width0

    x = np.arange(cfg.n, dtype=float)
    x0 = (cfg.n - 1) / 2.0

    # Base drift (open-loop should degrade slowly)
    drift_w = float(cfg.alpha) * 0.0015

    # Controller authority
    kw = 6.0
    kp = 4.0

    # Structural losses
    kspread = 0.003
    k_lam = float(cfg.lam) * 0.25

    k_base_decay = 0.00002  # prevents noise pumping peak above baseline

    # High-gain penalties (this is the important part)
    noise_gain_mult = 30.0     # amplifies noise when gain is large (jitter gets hurt)
    k_gain_loss = 0.0040       # mild per-step loss proportional to gain (prevents "free wins")
    k_gain_widen = 0.0006      # mild widening proportional to gain (forces controller to be sane)

    steps = int(cfg.steps)

    width_series = []
    peak_series = []
    gain_series = []
    chi_series = []
    norm_series = []

    for t in range(steps):
        obs = {"step": t, "width": width, "peak": peak, "width0": width0, "peak0": peak0}
        gain = float(controller.step(obs))

        chi_eff = cfg.chi_base * (1.0 + gain)
        if hasattr(controller, "chi_cap"):
            chi_eff = min(chi_eff, float(controller.chi_cap) * cfg.chi_base)

        # Noise increases with gain (jitter controllers pay for large random gains)
        noise_scale = 1.0 + noise_gain_mult * max(0.0, gain)
        nw = float(rng.normal(0.0, cfg.noise_std)) * 0.15 * noise_scale
        na = float(rng.normal(0.0, cfg.noise_std)) * 0.10 * noise_scale

        # Width dynamics: diffusion drift + gain-widen penalty + noise - corrective pull
        width = width + drift_w + k_gain_widen * gain + nw - kw * gain * (width - width0)
        if width < 1e-3:
            width = 1e-3

        # Peak dynamics: widening loss + gain-loss + corrective pull + mild relaxation + noise
        peak = (
            peak
            - kspread * max(0.0, width - width0)
            - k_gain_loss * gain
            + kp * gain * (peak0 - peak)
            - k_lam * (peak - peak0)
            - k_base_decay * peak
            + na
        )
        if peak < 1e-6:
            peak = 1e-6
        if peak > cfg.clip:
            peak = cfg.clip

        u = peak * np.exp(-0.5 * ((x - x0) / width) ** 2)
        u = np.clip(u, -cfg.clip, cfg.clip)
        norm = float(np.linalg.norm(u))

        width_series.append(float(width))
        peak_series.append(float(peak))
        gain_series.append(float(gain))
        chi_series.append(float(chi_eff))
        norm_series.append(norm)

    peakT = float(peak_series[-1])
    widthT = float(width_series[-1])

    # raw retention can exceed 1.0 due to noise; clamp + effort-penalize for audit-safe scoring
    peak_retention_raw = peakT / max(1e-12, peak0)
    peak_retention = max(0.0, min(1.0, peak_retention_raw))
    # penalize high-variance control (random jitter should lose)
    try:
        import numpy as _np
        _eff = 0.0
        _gs = gain_series if 'gain_series' in locals() else None
        _cs = chi_series  if 'chi_series'  in locals() else None
        if isinstance(_gs, list) and len(_gs) > 1: _eff += float(_np.std(_gs))
        if isinstance(_cs, list) and len(_cs) > 1: _eff += 0.5 * float(_np.std(_cs))
        _k = 2.0
        peak_retention = max(0.0, peak_retention - _k * _eff)
    except Exception:
        pass
    width_drift_pct = abs(widthT - width0) / max(1e-12, width0) * 100.0
    max_norm = float(np.max(norm_series))

    run_hash = _run_hash(test_id, cfg, getattr(controller, "name", controller.__class__.__name__), seed)

    run = {
        "test_id": test_id,
        "run_hash": run_hash,
        "controller": getattr(controller, "name", controller.__class__.__name__),
        "seed": seed,

        "peak0": peak0,
        "peakT": peakT,
        "width0": width0,
        "widthT": widthT,

        "peak_retention": float(peak_retention),
        "width_drift_pct": float(width_drift_pct),
        "max_norm": float(max_norm),

        "peak_series": peak_series,
        "width_series": width_series,
        "gain_series": gain_series,
        "chi_series": chi_series,
        "norm_series": norm_series,
    }

    if write_artifacts:
        from .artifacts import write_run_artifacts
        write_run_artifacts(cfg=cfg, run=run)

    return run
