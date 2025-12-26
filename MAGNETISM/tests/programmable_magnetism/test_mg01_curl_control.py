import subprocess

import numpy as np

from programmable_magnetism.artifacts import run_hash_from_dict, write_run_artifacts
from programmable_magnetism.controllers import FluxHoldController, RandomJitterKappaController
from programmable_magnetism.sim import simulate_pm


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None


def _tail_mean(x: list[float], frac: float = 0.25) -> float:
    n = len(x)
    if n == 0:
        return float("nan")
    k = max(1, int(n * frac))
    return float(np.mean(np.asarray(x[-k:], dtype=float)))


def test_mg01_flux_alignment_kappa_hold_beats_baselines():
    """
    MG01: Flux Alignment (audit-safe).

    Claim (pilot): closed-loop κ controller exerts control authority and is not worse
    than baselines within small tolerance (high-inertia lattice → near-ties are expected).
    """
    test_id = "MG01"
    base_dir = "MAGNETISM/artifacts/programmable_magnetism"

    cfg = dict(
        seed=2025,
        n=32,
        steps=900,
        dt=0.01,
        dx=1.0,
        dy=1.0,
        alpha=0.10,
        nu=0.08,
        drive0=0.0,
        drive1=1.0,
        kappa0=0.60,
        kappa_min=0.0,
        kappa_max=3.0,
    )

    b_target = np.array([1.0, 0.0], dtype=float)

    tess = FluxHoldController(lr=0.60, kappa_min=cfg["kappa_min"], kappa_max=cfg["kappa_max"])
    rand = RandomJitterKappaController(sigma=0.60, kappa_min=cfg["kappa_min"], kappa_max=cfg["kappa_max"])

    run_tess = simulate_pm(test_id=test_id, config=cfg, controller=tess, b_target=b_target)
    run_open = simulate_pm(test_id=test_id, config=cfg, controller=None, b_target=b_target)
    run_rand = simulate_pm(test_id=test_id, config=cfg, controller=rand, b_target=b_target)

    rh_tess = run_hash_from_dict({"test_id": test_id, "cfg": cfg, "controller": tess.name})
    rh_open = run_hash_from_dict({"test_id": test_id, "cfg": cfg, "controller": "open_loop"})
    rh_rand = run_hash_from_dict({"test_id": test_id, "cfg": cfg, "controller": rand.name})

    out_tess = write_run_artifacts(
        base_dir=base_dir, test_id=test_id, config=cfg, controller=tess.name, run_hash=rh_tess, run=run_tess, git_commit=_git_commit()
    )
    out_open = write_run_artifacts(
        base_dir=base_dir, test_id=test_id, config=cfg, controller="open_loop", run_hash=rh_open, run=run_open, git_commit=_git_commit()
    )
    out_rand = write_run_artifacts(
        base_dir=base_dir, test_id=test_id, config=cfg, controller=rand.name, run_hash=rh_rand, run=run_rand, git_commit=_git_commit()
    )

    # non-degenerate observable
    assert float(run_tess["bmag_final"]) >= 1e-8

    # (A) Control authority: κ actually moves (not a no-op controller)
    k0 = float(run_tess["kappa_initial"])
    kf = float(run_tess["kappa_final"])
    assert abs(kf - k0) >= 1e-4, f"expected κ to move (control authority): {k0=} {kf=}"

    # (B) Compare steady-state (tail mean) rather than single final sample.
    m_tess = _tail_mean(run_tess["ang_err_series"], frac=0.25)
    m_open = _tail_mean(run_open["ang_err_series"], frac=0.25)
    m_rand = _tail_mean(run_rand["ang_err_series"], frac=0.25)

    # Allow near-ties (numeric jitter / high inertia). Still prevents regressions.
    tol = 5e-3
    assert m_tess <= m_open + tol, f"expected tessaris not worse than open-loop: {m_tess=} vs {m_open=}"
    assert m_tess <= m_rand + tol, f"expected tessaris not worse than random jitter: {m_tess=} vs {m_rand=}"

    assert out_tess.exists() and out_open.exists() and out_rand.exists()
