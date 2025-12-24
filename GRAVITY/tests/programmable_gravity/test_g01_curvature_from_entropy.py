from __future__ import annotations

from pathlib import Path
import numpy as np

from programmable_gravity.config import PGConfig
from programmable_gravity.ops import gaussian_2d, laplacian_periodic
from programmable_gravity.sim import simulate_pg
from programmable_gravity.controllers import CurvatureHoldController, RandomJitterController
from programmable_gravity.artifacts import write_run_artifacts, run_hash_from_dict


def _git_commit() -> str | None:
    # best-effort: CI/local may not have git available
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return out
    except Exception:
        return None


def test_g01_curvature_from_entropy_beats_baselines(tmp_path: Path) -> None:
    """
    G01: Curvature From Entropy (deterministic, reviewer-proof)

    - Define S_target as a centered Gaussian entropy well.
    - Define R_target = Laplacian(S_target) as curvature proxy target.
    - Start from flat S0 plus small deterministic noise.
    - Under drift, controller should drive R_final toward R_target better than baselines.

    Artifacts are written to GRAVITY/artifacts/programmable_gravity/G01/<run_hash>/ (repo-relative).
    """
    cfg = PGConfig(
        N=128,
        steps=80,
        seed=1,
        drift_sigma=1e-3,
        well_sigma=10.0,
        well_amp=10.0,
        tups_version="TUPS_V1.2",
    )

    S_target = gaussian_2d(cfg.N, sigma=cfg.well_sigma, amp=cfg.well_amp)
    R_target = laplacian_periodic(S_target)

    rng0 = np.random.default_rng(cfg.seed)
    S0 = np.zeros((cfg.N, cfg.N), dtype=float) + rng0.normal(
        0.0, 1e-3, size=(cfg.N, cfg.N)
    )

    tess_ctrl = CurvatureHoldController(lr=0.25, max_step=0.25)
    rand_ctrl = RandomJitterController(sigma=0.02)

    test_id = "G01"

    run_tess = simulate_pg(test_id=test_id, config=cfg, controller=tess_ctrl, S0=S0, R_target=R_target)
    run_open = simulate_pg(test_id=test_id, config=cfg, controller=None, S0=S0, R_target=R_target)
    run_rand = simulate_pg(test_id=test_id, config=cfg, controller=rand_ctrl, S0=S0, R_target=R_target)

    mse_tess = float(run_tess["mse_final"])
    mse_open = float(run_open["mse_final"])
    mse_rand = float(run_rand["mse_final"])

    # Core asserts: beat baselines + absolute sanity
    assert mse_tess <= 0.25 * mse_open + 1e-12, (
        f"Expected Tessaris to beat open-loop: {mse_tess=} vs {mse_open=}"
    )
    assert mse_tess <= mse_rand + 1e-12, (
        f"Expected Tessaris to beat random jitter: {mse_tess=} vs {mse_rand=}"
    )
    assert mse_tess <= 2e-2, f"Expected tight curvature match: {mse_tess=}"

    # --- Artifacts (repo-relative path; do NOT use tmp_path for final storage) ---
    base_dir = "GRAVITY/artifacts/programmable_gravity"
    git_commit = _git_commit()

    def _emit(run: dict, controller_name: str) -> Path:
        meta = {
            "test_id": test_id,
            "controller": controller_name,
            "config": cfg.to_dict(),
            "git_commit": git_commit,
            "mse_final": float(run["mse_final"]),
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

    # sanity: artifact folders exist
    assert out_tess.exists() and out_open.exists() and out_rand.exists()
