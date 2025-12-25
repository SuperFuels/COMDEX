from __future__ import annotations

from pathlib import Path
import subprocess

from programmable_inertia.config import PIConfig
from programmable_inertia.controllers import AlphaHoldController, RandomJitterAlphaController
from programmable_inertia.sim import simulate_pi
from programmable_inertia.artifacts import write_run_artifacts, run_hash_from_dict


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def test_i01_inertial_scaling_alpha_control_beats_baselines() -> None:
    """
    I01 — Inertial Scaling (deterministic)

    Plant: dv/dt = drive - alpha*v
    Terminal velocity v_inf = drive/alpha.

    Choose v_target > drive/alpha0 so OPEN-LOOP cannot reach it.
    Controller must reduce alpha (within bounds) so v_final approaches v_target.
    """
    cfg = PIConfig(
        steps=200,
        dt=0.05,
        seed=7,
        drive=1.0,
        alpha0=0.5,      # open-loop v_inf = 2.0
        alpha_min=0.05,
        alpha_max=2.0,
        noise_sigma=0.0,
        tups_version="TUPS_V1.2",
    )

    v0 = 0.0
    v_target = 3.0       # > 2.0 => open-loop must miss

    tess_ctrl = AlphaHoldController(lr=0.02, max_delta=0.02, alpha_min=cfg.alpha_min, alpha_max=cfg.alpha_max)
    rand_ctrl = RandomJitterAlphaController(sigma=0.05, alpha_min=cfg.alpha_min, alpha_max=cfg.alpha_max)

    test_id = "I01"

    run_tess = simulate_pi(test_id=test_id, config=cfg, controller=tess_ctrl, v0=v0, v_target=v_target)
    run_open = simulate_pi(test_id=test_id, config=cfg, controller=None, v0=v0, v_target=v_target)
    run_rand = simulate_pi(test_id=test_id, config=cfg, controller=rand_ctrl, v0=v0, v_target=v_target)

    err_tess = float(run_tess["err_final"])
    err_open = float(run_open["err_final"])
    err_rand = float(run_rand["err_final"])

    # Core asserts: Tessaris beats baselines + absolute sanity
    assert err_tess <= 0.30 * err_open + 1e-12, f"Expected Tessaris to beat open-loop: {err_tess=} vs {err_open=}"
    assert err_tess <= err_rand + 1e-12, f"Expected Tessaris to beat random jitter: {err_tess=} vs {err_rand=}"
    assert err_tess <= 0.25, f"Expected tight velocity target hit: {err_tess=}"

    # Artifacts
    base_dir = "INERTIA/artifacts/programmable_inertia"
    git_commit = _git_commit()

    def _emit(run: dict, controller_name: str) -> Path:
        meta = {
            "test_id": test_id,
            "controller": controller_name,
            "config": cfg.to_dict(),
            "git_commit": git_commit,
            "err_final": float(run["err_final"]),
            "v_final": float(run["v_final"]),
            "v_target": float(run["v_target"]),
        }
        rh = run_hash_from_dict(meta)
        return write_run_artifacts(
            base_dir=base_dir,
            test_id=test_id,
            config=cfg.to_dict(),
            controller=controller_name,
            run_hash=rh,
            run=run,
            git_commit=git_commit,
        )

    out_tess = _emit(run_tess, tess_ctrl.name)
    out_open = _emit(run_open, "open_loop")
    out_rand = _emit(run_rand, rand_ctrl.name)

    assert out_tess.exists() and out_open.exists() and out_rand.exists()
