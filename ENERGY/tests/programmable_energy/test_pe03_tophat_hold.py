from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

ENERGY_ROOT = Path(__file__).resolve().parents[2]
SRC = ENERGY_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from programmable_energy.field import make_input_field
from programmable_energy.controllers import (
    PEConfig, OpenLoopController, SPGDController, TessarisGSController,
    target_tophat_intensity, simulate_pe,
)
from programmable_energy.artifacts import write_run_artifacts
from programmable_energy.metrics import roi_mask_circle

ART_BASE = str(ENERGY_ROOT / "artifacts" / "programmable_energy")

def _run_one(controller, cfg: PEConfig, test_id: str, target_I: np.ndarray):
    U_in = make_input_field(cfg.N, seed=cfg.seed)
    run = simulate_pe(
        test_id=test_id,
        controller=controller,
        config=cfg,
        U_in=U_in,
        target_I=target_I,
    )
    out_dir = write_run_artifacts(ART_BASE, test_id, run["run_hash"], run)
    return run, out_dir

def _flatness_std_over_mean(I: np.ndarray, mask: np.ndarray) -> float:
    vals = I[mask].astype(float)
    mu = float(np.mean(vals)) + 1e-12
    sd = float(np.std(vals))
    return sd / mu

def test_pe03_tophat_hold_tessaris_beats_baselines():
    """
    PE03: Closed-loop control approximates a top-hat disk intensity profile under disturbance.
    We evaluate by shape error (MSE vs target) + flatness inside disk (std/mean), relative to baselines.
    """
    cfg = PEConfig(
        N=256,
        steps=60,
        seed=1337,
        drift_sigma=0.05,
        roi_radius=10,   # unused for PE03 but kept consistent with PEConfig
        tups_version="TUPS_V1.2",
    )

    test_id = "PE03"
    radius = 18
    target_I = target_tophat_intensity(cfg.N, radius=radius)

    open_loop = OpenLoopController(cfg.N)
    spgd = SPGDController(cfg.N, rng=np.random.default_rng(cfg.seed), delta=0.05, lr=0.4)
    tessaris = TessarisGSController(cfg.N, max_phase_step=0.5, inner_iters=8, roi_weight=0.95)

    run_open, _ = _run_one(open_loop, cfg, test_id, target_I)
    run_spgd, _ = _run_one(spgd, cfg, test_id, target_I)
    run_tess, out_dir = _run_one(tessaris, cfg, test_id, target_I)

    # Load final intensities from artifacts (keeps this audit-friendly)
    I_open = np.load(Path(ART_BASE) / test_id / run_open["run_hash"] / "final_intensity.npy")
    I_spgd = np.load(Path(ART_BASE) / test_id / run_spgd["run_hash"] / "final_intensity.npy")
    I_tess = np.load(Path(ART_BASE) / test_id / run_tess["run_hash"] / "final_intensity.npy")

    # 1) Shape error (MSE vs target)
    mse_open = float(np.mean((I_open - target_I) ** 2))
    mse_spgd = float(np.mean((I_spgd - target_I) ** 2))
    mse_tess = float(np.mean((I_tess - target_I) ** 2))

    # 2) Flatness inside disk (std/mean)
    disk_mask = roi_mask_circle(cfg.N, radius)
    flat_open = _flatness_std_over_mean(I_open, disk_mask)
    flat_spgd = _flatness_std_over_mean(I_spgd, disk_mask)
    flat_tess = _flatness_std_over_mean(I_tess, disk_mask)

    # Must beat baselines
    assert mse_tess <= mse_open + 1e-12, f"tessaris MSE not beating open-loop (see {out_dir})"
    assert mse_tess <= mse_spgd + 1e-12, f"tessaris MSE not beating SPGD (see {out_dir})"
    assert flat_tess <= flat_open + 1e-12, f"tessaris flatness not beating open-loop (see {out_dir})"
    assert flat_tess <= flat_spgd + 1e-12, f"tessaris flatness not beating SPGD (see {out_dir})"

    # Loose absolute sanity (tighten after first VERIFIED run)
    assert mse_tess <= 5e-5, f"MSE too high: {mse_tess} (see {out_dir})"

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
