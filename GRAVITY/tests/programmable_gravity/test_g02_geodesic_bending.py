from __future__ import annotations

import os
from pathlib import Path
import subprocess

import numpy as np

from programmable_gravity.config import PGConfig
from programmable_gravity.ops import gaussian_2d, laplacian_periodic
from programmable_gravity.sim import simulate_pg
from programmable_gravity.controllers import CurvatureHoldController, RandomJitterController
from programmable_gravity.artifacts import write_run_artifacts, run_hash_from_dict
from programmable_gravity.rays import trace_rays_through_potential


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def test_g02_geodesic_bending_controller_preserves_lens(tmp_path: Path) -> None:
    """
    G02: Geodesic Bending (lensing analogue)

    - Define S_target as a centered Gaussian entropy well.
    - Use Phi := Laplacian(S_final) as "curvature potential" proxy.
    - Trace deterministic rays through Phi.
    - Under drift, controller should preserve stronger bending vs open-loop and random jitter.
    - Artifacts saved to: GRAVITY/artifacts/programmable_gravity/G02/<run_hash>/
    """
    cfg = PGConfig(
        N=128,
        steps=90,
        seed=1,
        drift_sigma=2e-3,   # stronger drift than G01 to make lens decay open-loop
        well_sigma=10.0,
        well_amp=10.0,
        tups_version="TUPS_V1.2",
    )

    S_target = gaussian_2d(cfg.N, sigma=cfg.well_sigma, amp=cfg.well_amp)
    R_target = laplacian_periodic(S_target)

    rng0 = np.random.default_rng(cfg.seed)
    S0 = rng0.normal(0.0, 1e-3, size=(cfg.N, cfg.N))

    tess_ctrl = CurvatureHoldController(lr=0.05, max_step=0.02)
    rand_ctrl = RandomJitterController(sigma=0.02)

    test_id = "G02"

    run_tess = simulate_pg(test_id=test_id, config=cfg, controller=tess_ctrl, S0=S0, R_target=R_target)
    run_open = simulate_pg(test_id=test_id, config=cfg, controller=None,    S0=S0, R_target=R_target)
    run_rand = simulate_pg(test_id=test_id, config=cfg, controller=rand_ctrl, S0=S0, R_target=R_target)

    base_dir = "GRAVITY/artifacts/programmable_gravity"
    git_commit = _git_commit()

    def _emit(run: dict, controller_name: str) -> Path:
        meta = {
            "test_id": test_id,
            "controller": controller_name,
            "config": cfg.to_dict(),
            "git_commit": git_commit,
        }
        rh = run_hash_from_dict(meta)
        out = write_run_artifacts(
            base_dir=base_dir,
            test_id=test_id,
            config=cfg.to_dict(),
            controller=controller_name,
            run_hash=rh,
            run=run,
            git_commit=git_commit,
        )
        return out

    out_tess = _emit(run_tess, tess_ctrl.name)
    out_open = _emit(run_open, "open_loop")
    out_rand = _emit(run_rand, rand_ctrl.name)

    # Load final S from artifacts (robust across sim return shapes)
    S_tess = np.load(out_tess / "S_final.npy")
    S_open = np.load(out_open / "S_final.npy")
    S_rand = np.load(out_rand / "S_final.npy")

    Phi_tess = laplacian_periodic(S_tess)
    Phi_open = laplacian_periodic(S_open)
    Phi_rand = laplacian_periodic(S_rand)

    # Ray bending metric
    r_tess = trace_rays_through_potential(Phi_tess, n_rays=32, n_steps=240, dt=0.15)
    r_open = trace_rays_through_potential(Phi_open, n_rays=32, n_steps=240, dt=0.15)
    r_rand = trace_rays_through_potential(Phi_rand, n_rays=32, n_steps=240, dt=0.15)

    # Compare against TARGET lensing (hold the programmed curvature, not "maximize bending")
    Phi_target = laplacian_periodic(S_target)
    r_target = trace_rays_through_potential(Phi_target, n_rays=32, n_steps=240, dt=0.15)

    defl_target = r_target.deflection_mean_abs
    err_tess = abs(r_tess.deflection_mean_abs - defl_target)
    err_open = abs(r_open.deflection_mean_abs - defl_target)
    err_rand = abs(r_rand.deflection_mean_abs - defl_target)

    # Core asserts: Tessaris should HOLD lensing closest to target
    assert err_tess <= 0.30 * err_open + 1e-12, (
    f"Expected Tessaris closer to target than open-loop: {err_tess=} vs {err_open=} (defl_target={defl_target})"
)
    assert err_tess <= err_rand + 1e-12, (
    f"Expected Tessaris closer to target than random jitter: {err_tess=} vs {err_rand=} (defl_target={defl_target})"
)

    # sanity: artifact dirs exist
    assert out_tess.exists() and out_open.exists() and out_rand.exists()
