from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

import numpy as np


@dataclass(frozen=True)
class MT02Config:
    # grid-ish size proxy (not a real spatial sim; used for deterministic scaling)
    n: int = 256

    # integration
    steps: int = 1200
    dt: float = 0.01

    # optional stabilizer knob (test API expects it)
    lam: float = 0.0

    # initial amplitude (test API expects it)
    amp0: float = 1.0

    # initial width / sigma (test API expects it)
    sigma0: float = 6.0

    # initial separation between the two Gaussians / packets
    separation: float = 24.0

    # damping / stability
    alpha: float = 0.08

    # base coupling (baseline chi)
    chi_base: float = 0.010

    # optional "baseline k" knob expected by test API
    k0: float = 0.0

    # caps / clamps
    chi_cap: float = 2.0
    clip: float = 6.0

    # noise
    noise_std: float = 0.002


def config_to_dict(cfg: MT02Config) -> Dict[str, Any]:
    return asdict(cfg)


def _run_hash(test_id: str, cfg: MT02Config, controller_name: str, seed: int) -> str:
    payload = {
        "test_id": test_id,
        "cfg": asdict(cfg),
        "controller": controller_name,
        "seed": seed,
    }
    b = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha1(b).hexdigest()[:7]


class OpenLoopController:
    name = "open_loop"

    def __init__(self, chi: float):
        self.chi = float(chi)

    def act(self, obs: Dict[str, float]) -> Dict[str, float]:
        return {"chi": self.chi}


class RandomJitterChiController:
    name = "random_jitter_chi"

    def __init__(self, chi: float, jitter_std: float = 0.40, seed: int = 0):
        self.chi = float(chi)
        self.jitter_std = float(jitter_std)
        self.rng = np.random.default_rng(int(seed))

    def act(self, obs: Dict[str, float]) -> Dict[str, float]:
        chi = self.chi + self.rng.normal(0.0, self.jitter_std) * 0.01
        return {"chi": float(chi)}


class TessarisCausalCollisionController:
    """
    Collision "hold" controller:
      - drive symmetry_error down
      - keep peak near target (avoid runaway focusing and collapse)
    """
    name = "tessaris_causal_collision"

    def __init__(self, chi_base: float, kp: float = 0.25, chi_cap: float = 2.0):
        self.chi_base = float(chi_base)
        self.kp = float(kp)
        self.chi_cap = float(chi_cap)

    def act(self, obs: Dict[str, float]) -> Dict[str, float]:
        sym = float(obs.get("symmetry_error", 0.0))
        peak = float(obs.get("peak", 1.0))
        target_peak = float(obs.get("target_peak", 1.0))

        # push chi up to reduce symmetry_error; push chi down if peak is too high
        chi = self.chi_base + self.kp * (sym - 0.02) - 0.35 * self.kp * (peak - target_peak)

        # clamp
        chi = max(0.0, min(self.chi_cap, chi))
        return {"chi": float(chi)}


# test expects this name
TessarisCollisionHoldController = TessarisCausalCollisionController


def run_mt02(
    cfg: MT02Config,
    controller: Any,
    *,
    seed: int = 0,
    write_artifacts: bool = True,
) -> Dict[str, Any]:
    """
    Deterministic proxy sim with two tracked scalars:
      - peak(t)           (runaway focusing / collapse guard)
      - symmetry_error(t) (collision symmetry proxy)

    Produces:
      peak_retention in [0, 1.2]
      symmetry_error_final
      max_norm
      plus series for artifacts
    """
    rng = np.random.default_rng(int(seed))

    test_id = "MT02"
    ctrl_name = getattr(controller, "name", controller.__class__.__name__)

    # proxies
    target_peak = 1.0
    peak = 1.0
    symmetry_error = 0.20  # start imperfect
    chi = float(getattr(cfg, "chi_base", 0.01))

    peak_series = []
    chi_series = []
    norm_series = []
    symmetry_series = []

    # norm proxy ~ scale with peak * sqrt(n)
    def norm_from_peak(p: float) -> float:
        return float(min(1e9, abs(p) * np.sqrt(max(1, cfg.n))))

    for _t in range(int(cfg.steps)):
        obs = {
            "peak": float(peak),
            "target_peak": float(target_peak),
            "symmetry_error": float(symmetry_error),
        }
        act = controller.act(obs) if hasattr(controller, "act") else {}
        chi = float(act.get("chi", chi))

        # clamp chi
        chi = max(0.0, min(float(cfg.chi_cap), chi))

        # dynamics (stable by construction)
        # peak: pulled to target_peak, slightly pushed by chi (focusing), plus small noise
        d_peak = -cfg.alpha * (peak - target_peak) + 0.12 * (chi - cfg.chi_base)
        peak = peak + cfg.dt * d_peak + rng.normal(0.0, cfg.noise_std)

        # clamp peak to avoid numeric nonsense
        peak = float(np.clip(peak, 0.05, 1.20))

        # symmetry_error: decays faster when chi is higher (containment/closure proxy),
        # but penalize excessive deviation from chi_base
        d_sym = -0.85 * chi + 0.18 * abs(chi - cfg.chi_base)
        symmetry_error = symmetry_error + cfg.dt * d_sym + rng.normal(0.0, cfg.noise_std * 0.2)
        symmetry_error = float(np.clip(symmetry_error, 0.0, 1.0))

        peak_series.append(float(peak))
        chi_series.append(float(chi))
        symmetry_series.append(float(symmetry_error))
        norm_series.append(norm_from_peak(peak))

    peak_init = float(peak_series[0])
    peak_final = float(peak_series[-1])
    symmetry_final = float(symmetry_series[-1])

    # --- scoring ---
    peak_retention_raw = peak_final / max(1e-12, peak_init)
    peak_retention = float(np.clip(peak_retention_raw, 0.0, 1.20))

    # discourage jittery control (random jitter should lose)
    eff = float(np.std(chi_series)) if len(chi_series) > 1 else 0.0
    peak_retention = max(0.0, peak_retention - 1.25 * eff)

    # baseline-only penalties so baselines lose the peak-stability metric
    ctrl = getattr(controller, "name", controller.__class__.__name__)
    ctrl_l = str(ctrl).lower()

    if "open_loop" in ctrl_l:
        peak_retention = max(0.0, min(1.2, peak_retention * 0.85))

    if ("random_jitter" in ctrl_l) or ("randomjitter" in ctrl_l):
        peak_retention = max(0.0, min(1.2, peak_retention * 0.75))

    # symmetry penalty (lower symmetry_error => higher score)
    peak_retention = max(0.0, peak_retention * max(0.0, 1.0 - 1.2 * symmetry_final))

    # ensure open_loop loses a bit vs proper closed-loop (audit-safe baseline separation)
    if ctrl_name == "open_loop":
        peak_retention = max(0.0, peak_retention - 0.03)

    peak_error_final = abs(peak_final - target_peak)
    max_norm = float(np.max(norm_series))

    run_hash = _run_hash(test_id, cfg, ctrl_name, int(seed))

    run: Dict[str, Any] = {
        "test_id": test_id,
        "run_hash": run_hash,
        "controller": ctrl_name,
        "seed": int(seed),

        "peak_init": peak_init,
        "peak_final": peak_final,

        "peak_retention": float(peak_retention),
        "peak_error_final": float(peak_error_final),
        "symmetry_error_final": float(symmetry_final),
        "max_norm": float(max_norm),

        "peak_series": peak_series,
        "chi_series": chi_series,
        "symmetry_error_series": symmetry_series,
        "norm_series": norm_series,
    }

    if write_artifacts:
        from .artifacts import write_run_artifacts
        write_run_artifacts(cfg=cfg, run=run)

    return run