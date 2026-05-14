from __future__ import annotations

from programmable_matter.sim_mt02 import (
    MT02Config,
    OpenLoopController,
    RandomJitterChiController,
    TessarisCollisionHoldController,
    run_mt02,
)


def test_mt02_causal_collision_beats_baselines():
    """
    MT02 (model-only): two solitons collide. We want a stable bound-state proxy:
    - no collapse (peak retention not too low)
    - no runaway (peak retention not too high)
    - symmetry preserved
    - bounded norm
    """
    cfg = MT02Config(
        n=256,
        steps=1600,
        dt=0.06,
        alpha=0.055,
        lam=0.002,
        noise_std=0.0015,
        amp0=1.0,
        sigma0=6.0,
        separation=60.0,
        k0=0.32,
        chi_base=0.012,
        chi_cap=0.06,
        clip=6.0,
    )

    seed = 0
    norm_cap = 80.0

    tess = TessarisCollisionHoldController(chi_base=cfg.chi_base, kp=0.25, chi_cap=cfg.chi_cap)
    open_loop = OpenLoopController(chi=cfg.chi_base)
    jitter = RandomJitterChiController(chi=cfg.chi_base, jitter_std=0.40, seed=seed)

    r_tess = run_mt02(cfg, tess, seed=seed)
    r_open = run_mt02(cfg, open_loop, seed=seed)
    r_jit = run_mt02(cfg, jitter, seed=seed)

    # boundedness guardrail
    assert r_tess["max_norm"] <= norm_cap, "unexpected instability (norm blow-up)"

    # peak stability: want peak_retention close to 1.0 (no decay, no runaway)
    e_tess = abs(1.0 - r_tess["peak_retention"])
    e_open = abs(1.0 - r_open["peak_retention"])
    e_jit = abs(1.0 - r_jit["peak_retention"])

    assert r_tess["peak_retention"] >= 0.85, "collapsed too far"
    assert r_tess["peak_retention"] <= 1.20, "runaway focusing"
    assert e_tess <= e_open - 0.05, "should stabilize peak better than open-loop"
    assert e_tess <= e_jit - 0.05, "should stabilize peak better than jitter baseline"

    # symmetry guardrail
    assert r_tess["symmetry_error_final"] <= 0.15
