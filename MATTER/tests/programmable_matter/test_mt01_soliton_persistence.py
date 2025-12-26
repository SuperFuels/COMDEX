from __future__ import annotations

from programmable_matter.sim import MT01Config, run_mt01
from programmable_matter.controllers import (
    TessarisSolitonHoldController,
    OpenLoopController,
    RandomJitterGainController,
)


def test_mt01_soliton_persistence_beats_baselines():
    """
    MT01: Soliton Persistence (model-only).

    Pass conditions:
      - Tessaris controller beats open-loop + random jitter on peak retention
      - Tessaris meets absolute stability requirements:
          peak_retention >= 0.90
          width_drift_pct <= 2.0
          max_norm <= norm_cap
    """
    cfg = MT01Config(
        n=256,
        steps=5000,
        alpha=0.06,
        lam=0.002,
        noise_std=0.002,
        amp0=1.0,
        sigma0=6.0,
        chi_base=0.008,
        clip=6.0,
    )

    seed = 1337
    norm_cap = 80.0

    tess = TessarisSolitonHoldController(
        base_gain=0.02,
        kp_width=0.004,
        kp_peak=0.004,
        gain_cap=0.25,
        chi_cap=2.0,
    )
    open_loop = OpenLoopController()
    jitter = RandomJitterGainController(gain_cap=0.25)

    r_tess = run_mt01(cfg, tess, seed=seed, write_artifacts=True)
    r_open = run_mt01(cfg, open_loop, seed=seed, write_artifacts=True)
    r_jit = run_mt01(cfg, jitter, seed=seed, write_artifacts=True)

    # must beat baselines
    assert r_tess["peak_retention"] >= r_open["peak_retention"] + 0.05
    assert r_tess["peak_retention"] >= r_jit["peak_retention"] + 0.05

    # absolute quality gates (tessaris only)
    assert r_tess["max_norm"] <= norm_cap, "unexpected instability (norm blow-up)"
    assert r_tess["peak_retention"] >= 0.90, "soliton peak did not persist"
    assert r_tess["width_drift_pct"] <= 2.0, "soliton width drift too large"
