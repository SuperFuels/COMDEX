import numpy as np

from programmable_inertia.controllers import AlphaHoldController, RandomJitterAlphaController
from programmable_inertia.relativistic import simulate_pi_relativistic
from programmable_inertia.artifacts import write_run_artifacts, run_hash_from_dict


def test_i02_relativistic_inertial_surge_alpha_decouples_and_tracks():
    """
    I02: saturation / cutoff proxy inside the lattice model (NOT a physical claim).

    Proves (model-level):
      - We can approach a causal ceiling proxy (c_eff) under a saturation wall.
      - Controller tracks v_target better than baselines.
      - Evidence of decoupling: alpha dips below alpha0 in the near-wall regime.
    """
    test_id = "I02"

    cfg = dict(
        seed=1337,
        steps=800,
        dt=0.01,
        c_eff=0.70710678,
        # start with higher drag to make open-loop worse; controller can decouple downwards
        alpha0=1.20,
        alpha_min=0.05,
        alpha_max=2.00,
        drive0=0.0,
        drive1=1.0,
    )

    c_eff = float(cfg["c_eff"])
    v_target = 0.7071 * c_eff
    v_floor = 0.60 * c_eff

    tess = AlphaHoldController(lr=0.25)
    rand = RandomJitterAlphaController(
        sigma=0.25, alpha_min=cfg["alpha_min"], alpha_max=cfg["alpha_max"]
    )

    run_tess = simulate_pi_relativistic(test_id=test_id, config=cfg, controller=tess, v_target=v_target)
    run_open = simulate_pi_relativistic(test_id=test_id, config=cfg, controller=None, v_target=v_target)
    run_rand = simulate_pi_relativistic(test_id=test_id, config=cfg, controller=rand, v_target=v_target)

    # --- artifacts (match INERTIA writer signature) ---
    rh_tess = run_hash_from_dict({**cfg, "controller": "tessaris_alpha_hold", "test_id": test_id})
    rh_open = run_hash_from_dict({**cfg, "controller": "open_loop", "test_id": test_id})
    rh_rand = run_hash_from_dict({**cfg, "controller": "random_jitter_alpha", "test_id": test_id})

    out_tess = write_run_artifacts(
        base_dir="INERTIA/artifacts/programmable_inertia",
        test_id=test_id,
        config=cfg,
        controller="tessaris_alpha_hold",
        run_hash=rh_tess,
        run=run_tess,
    )
    out_open = write_run_artifacts(
        base_dir="INERTIA/artifacts/programmable_inertia",
        test_id=test_id,
        config=cfg,
        controller="open_loop",
        run_hash=rh_open,
        run=run_open,
    )
    out_rand = write_run_artifacts(
        base_dir="INERTIA/artifacts/programmable_inertia",
        test_id=test_id,
        config=cfg,
        controller="random_jitter_alpha",
        run_hash=rh_rand,
        run=run_rand,
    )

    v_tess = float(run_tess["v_final"])
    v_open = float(run_open["v_final"])
    v_rand = float(run_rand["v_final"])

    err_tess = abs(v_tess - v_target)
    err_open = abs(v_open - v_target)
    err_rand = abs(v_rand - v_target)

    # (1) enter high-velocity regime (model-level)
    assert v_tess >= v_floor - 1e-12, f"expected high-velocity reach: {v_tess=} vs {v_floor=}"

    # (2) controller dominance
    assert err_tess <= 0.75 * err_open + 1e-12, f"expected tessaris to beat open-loop: {err_tess=} vs {err_open=}"
    assert err_tess <= err_rand + 1e-12, f"expected tessaris to beat random jitter: {err_tess=} vs {err_rand=}"

    # (3) evidence of active decoupling near the wall (don’t require alpha_final < alpha0)
    a0 = float(run_tess.get("alpha_initial", np.nan))
    assert np.isfinite(a0), "run must emit alpha_initial for audit"

    v_series = np.asarray(run_tess.get("v_series", []), dtype=float)
    a_series = np.asarray(run_tess.get("alpha_series", []), dtype=float)
    assert v_series.size == a_series.size and v_series.size > 5, "run must emit v_series/alpha_series for I02"

    mask = v_series >= (v_floor * 0.98)
    assert mask.any(), "expected to enter near-wall region"

    a_min = float(np.min(a_series[mask]))
    assert a_min < a0 - 1e-6, f"expected alpha to decouple at high v: min(alpha)={a_min} vs alpha0={a0}"

    # optional: show negative correlation between v and alpha near wall
    if np.sum(mask) >= 6:
        corr = float(np.corrcoef(v_series[mask], a_series[mask])[0, 1])
        assert corr < 0.0, f"expected negative corr between v and alpha near wall: corr={corr}"

    # (4) sanity: artifact dirs exist
    assert out_tess.exists() and out_open.exists() and out_rand.exists()
