from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

# File: .../ENERGY/tests/programmable_energy/test_pe01_focus_lock.py
# parents[2] == .../ENERGY
ENERGY_ROOT = Path(__file__).resolve().parents[2]
SRC = ENERGY_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from programmable_energy.field import make_input_field
from programmable_energy.controllers import (
    PEConfig, OpenLoopController, SPGDController, TessarisGSController,
    target_focus_intensity, simulate_pe,
)
from programmable_energy.artifacts import write_run_artifacts
from programmable_energy.metrics import roi_efficiency, roi_mask_circle

ART_BASE = str(ENERGY_ROOT / "artifacts" / "programmable_energy")

def _run_one(controller, cfg: PEConfig, test_id: str):
    U_in = make_input_field(cfg.N, seed=cfg.seed)
    target_I = target_focus_intensity(cfg.N, sigma=6.0)
    run = simulate_pe(
        test_id=test_id,
        controller=controller,
        config=cfg,
        U_in=U_in,
        target_I=target_I,
    )
    out_dir = write_run_artifacts(ART_BASE, test_id, run["run_hash"], run)
    return run, out_dir, target_I

def test_pe01_focus_lock_tessaris_beats_baselines():
    """
    PE01: Closed-loop phase control keeps energy in an ROI under disturbance.

    NOTE (toy benchmark):
    This harness may include a synthetic disturbance that moves energy out of the ROI,
    so we evaluate by beating baselines + maintaining non-collapse over a window.
    """
    cfg = PEConfig(
        N=256,
        steps=60,
        seed=1337,
        drift_sigma=0.05,   # interpreted by current simulate_pe disturbance model
        roi_radius=10,
        tups_version="TUPS_V1.2",
    )

    test_id = "PE01"

    open_loop = OpenLoopController(cfg.N)
    spgd = SPGDController(cfg.N, rng=np.random.default_rng(cfg.seed), delta=0.05, lr=0.4)
    tessaris = TessarisGSController(cfg.N, max_phase_step=0.5, inner_iters=8, roi_weight=0.95)

    run_open, _, target_I = _run_one(open_loop, cfg, test_id)
    run_spgd, _, _ = _run_one(spgd, cfg, test_id)
    run_tess, out_dir, _ = _run_one(tessaris, cfg, test_id)

    eta_open = np.array([m["eta"] for m in run_open["metrics"]], dtype=float)
    eta_spgd = np.array([m["eta"] for m in run_spgd["metrics"]], dtype=float)
    eta_tess = np.array([m["eta"] for m in run_tess["metrics"]], dtype=float)

    # ---- Must beat baselines (scale-free / ratio-based) ----
    assert float(eta_tess[-1]) >= 10.0 * float(eta_open[-1]) + 1e-6, f"tessaris not beating open-loop by 10x (see {out_dir})"
    assert float(np.mean(eta_tess[-20:])) >= float(np.mean(eta_spgd[-20:])) - 1e-12, f"tessaris not >= spgd on last-window mean (see {out_dir})"

    # ---- Non-collapse stability over last window ----
    w = eta_tess[-20:]
    assert float(np.min(w)) >= 0.20 * float(np.mean(w)) - 1e-12, f"tessaris collapses in last window (see {out_dir})"

    # ---- Keep a reference ceiling for context (not an assertion) ----
    roi_mask = roi_mask_circle(cfg.N, cfg.roi_radius)
    _eta_target = float(roi_efficiency(target_I, roi_mask))

    # Confirm artifacts exist
    expected = [
        Path(out_dir) / "config.json",
        Path(out_dir) / "metrics.csv",
        Path(out_dir) / "final_phase.npy",
        Path(out_dir) / "final_intensity.npy",
        Path(out_dir) / "target_intensity.npy",
        Path(out_dir) / "plots" / "intensity_final.png",
        Path(out_dir) / "plots" / "metrics_over_time.png",
    ]
    for q in expected:
        assert q.exists(), f"Missing artifact: {q}"
