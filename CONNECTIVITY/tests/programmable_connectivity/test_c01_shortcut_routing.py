import subprocess
from pathlib import Path

from programmable_connectivity.artifacts import run_hash_from_dict, write_run_artifacts
from programmable_connectivity.controllers import (
    SigmaHoldController,
    OpenLoopController,
    RandomJitterSigmaController,
)
from programmable_connectivity.sim import simulate_connectivity

def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None

def test_c01_shortcut_routing_beats_baselines():
    """
    C01 (audit-safe): a throat-coupled controller reduces arrival_step vs baselines
    under fixed protocol constants + deterministic seed.
    """
    config = {
        "seed": 1337,
        "H": 96,
        "W": 96,
        "steps": 600,
        "dt": 0.05,

        # Protocol constants (pinned environment labels)
        "hbar": 1e-3,
        "G": 1e-5,
        "Lambda0": 1e-6,
        "alpha": 0.5,

        # Dynamics
        "nu": 0.18,
        "damp": 0.010,

        # Source / destination
        "src_xy": (12, 48),
        "dst_xy": (84, 48),

        # Correlation arrival metric
        "corr_window_r": 1,
        "C_thresh": 0.90,

        # Throat conductance (canon pin)
        "eta": 0.9974,
    }

    base_dir = Path("CONNECTIVITY/artifacts/programmable_connectivity")

    tess = SigmaHoldController(name="tessaris_sigma_hold", sigma=1.0)
    open_ = OpenLoopController(name="open_loop")
    rand = RandomJitterSigmaController(name="random_jitter_sigma", sigma0=0.5, sigma_step=0.12)

    r_tess = simulate_connectivity(test_id="C01", config=config, controller=tess)
    r_open = simulate_connectivity(test_id="C01", config=config, controller=open_)
    r_rand = simulate_connectivity(test_id="C01", config=config, controller=rand)

    h_tess = run_hash_from_dict({"test_id":"C01","controller":r_tess["controller"],"config":config})
    h_open = run_hash_from_dict({"test_id":"C01","controller":r_open["controller"],"config":config})
    h_rand = run_hash_from_dict({"test_id":"C01","controller":r_rand["controller"],"config":config})

    r_tess["git_commit"] = _git_commit()
    r_open["git_commit"] = _git_commit()
    r_rand["git_commit"] = _git_commit()

    write_run_artifacts(base_dir=base_dir, test_id="C01", run_hash=h_tess, run=r_tess)
    write_run_artifacts(base_dir=base_dir, test_id="C01", run_hash=h_open, run=r_open)
    write_run_artifacts(base_dir=base_dir, test_id="C01", run_hash=h_rand, run=r_rand)

    a_tess = r_tess["arrival_step"]
    a_open = r_open["arrival_step"]
    a_rand = r_rand["arrival_step"]

    assert a_tess <= 0.85 * a_open + 1e-12, f"expected tessaris to reduce arrival_step: {a_tess=} vs {a_open=}"
    assert a_tess <= a_rand + 1e-12, f"expected tessaris to beat random jitter: {a_tess=} vs {a_rand=}"

    assert max(r_tess["norm_series"]) <= 5.0, "unexpected instability (norm blow-up)"
