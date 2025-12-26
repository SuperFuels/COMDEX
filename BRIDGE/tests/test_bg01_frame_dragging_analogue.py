from programmable_bridge.sim_bg01 import (
    BG01Config,
    run_bg01,
    OpenLoopController,
    RandomJitterKappaController,
    TessarisCurlDriveController,
)


def test_bg01_frame_dragging_analogue_beats_baselines():
    cfg = BG01Config()

    # fixed seed for deterministic artifact + score
    seed = 1337

    tess = TessarisCurlDriveController(curl_target=cfg.curl_target, kp=6.0, kappa_cap=cfg.kappa_cap)
    open_loop = OpenLoopController(kappa=0.0)
    jitter = RandomJitterKappaController(kappa0=0.0, jitter_std=0.25, seed=seed, kappa_cap=cfg.kappa_cap)

    r_tess = run_bg01(cfg, tess, seed=seed, write_artifacts=True)
    r_open = run_bg01(cfg, open_loop, seed=seed, write_artifacts=True)
    r_jit = run_bg01(cfg, jitter, seed=seed, write_artifacts=True)

    # Coupling should be directionally consistent (positive in this model)
    assert r_tess["coupling_coeff"] > 0.0

    # Baseline beating (score includes effort penalty so jitter shouldn't win)
    assert r_tess["coupling_score"] >= r_open["coupling_score"] + 0.02
    assert r_tess["coupling_score"] >= r_jit["coupling_score"] + 0.02
 
    # Boundedness
    assert r_tess["max_norm"] <= 1e6