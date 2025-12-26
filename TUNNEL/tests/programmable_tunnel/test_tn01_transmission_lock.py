import subprocess

import numpy as np

from programmable_tunnel.artifacts import run_hash_from_dict, write_run_artifacts
from programmable_tunnel.controllers import RandomJitterBarrierController, TransmissionLockController
from programmable_tunnel.sim import simulate_tunnel


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None


def test_tn01_transmission_lock_beats_baselines():
    test_id = "TN01"
    base_dir = "TUNNEL/artifacts/programmable_tunnel"

    cfg = dict(
        seed=2025,
        n=512,
        steps=1600,
        dt=0.006,
        dx=0.02,
        nu=0.50,
        absorber_strength=0.03,
        absorber_width_frac=0.10,
        barrier_center=0.50,
        barrier_width_frac=0.06,
        v0=6.0,
        v0_min=0.0,
        v0_max=25.0,
        packet_x0=0.20,
        packet_sigma=0.35,
        packet_k0=7.0,
        measure_right_of=0.62,
    )

    # We don't assert any "magic" absolute transmission. We only show control authority:
    # closed-loop gets closer to a target than open-loop and random jitter.
    T_target = 0.40

    tess = TransmissionLockController(lr=8.0, v0_min=cfg["v0_min"], v0_max=cfg["v0_max"])
    rand = RandomJitterBarrierController(sigma=5.0, v0_min=cfg["v0_min"], v0_max=cfg["v0_max"])

    run_tess = simulate_tunnel(test_id=test_id, config=cfg, controller=tess, T_target=T_target)
    run_open = simulate_tunnel(test_id=test_id, config=cfg, controller=None, T_target=T_target)
    run_rand = simulate_tunnel(test_id=test_id, config=cfg, controller=rand, T_target=T_target)

    rh_tess = run_hash_from_dict({"test_id": test_id, "cfg": cfg, "controller": tess.name, "T_target": T_target})
    rh_open = run_hash_from_dict({"test_id": test_id, "cfg": cfg, "controller": "open_loop", "T_target": T_target})
    rh_rand = run_hash_from_dict({"test_id": test_id, "cfg": cfg, "controller": rand.name, "T_target": T_target})

    out_tess = write_run_artifacts(
        base_dir=base_dir,
        test_id=test_id,
        config={**cfg, "T_target": T_target},
        controller=tess.name,
        run_hash=rh_tess,
        run=run_tess,
        git_commit=_git_commit(),
    )
    out_open = write_run_artifacts(
        base_dir=base_dir,
        test_id=test_id,
        config={**cfg, "T_target": T_target},
        controller="open_loop",
        run_hash=rh_open,
        run=run_open,
        git_commit=_git_commit(),
    )
    out_rand = write_run_artifacts(
        base_dir=base_dir,
        test_id=test_id,
        config={**cfg, "T_target": T_target},
        controller=rand.name,
        run_hash=rh_rand,
        run=run_rand,
        git_commit=_git_commit(),
    )

    err_tess = float(run_tess["T_err_final"])
    err_open = float(run_open["T_err_final"])
    err_rand = float(run_rand["T_err_final"])

    # Non-degeneracy: must have non-zero norm and meaningful signal.
    assert float(run_tess["norm_final"]) >= 1e-6

    # Dominance: tessaris should improve target tracking.
    assert err_tess <= 0.90 * err_open + 1e-12, f"expected tessaris to beat open-loop: {err_tess=} vs {err_open=}"
    assert err_tess <= err_rand + 1e-12, f"expected tessaris to beat random jitter: {err_tess=} vs {err_rand=}"

    assert out_tess.exists() and out_open.exists() and out_rand.exists()
