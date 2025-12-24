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
    target_split_intensity, simulate_pe,
)
from programmable_energy.artifacts import write_run_artifacts

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

def _split_ratio(I: np.ndarray) -> float:
    N = I.shape[0]
    c = N // 2
    left = float(np.sum(I[:, :c]))
    right = float(np.sum(I[:, c:]))
    denom = left + right + 1e-12
    return left / denom

def test_pe02_split_ratio_tessaris_controls_ratio():
    """
    PE02: Closed-loop control targets a two-lobe split with a specified left/right energy ratio.
    """
    cfg = PEConfig(
        N=256,
        steps=60,
        seed=1337,
        drift_sigma=0.05,   # consistent with PE01
        roi_radius=10,
        tups_version="TUPS_V1.2",
    )

    test_id = "PE02"
    ratio_left = 0.70
    target_I = target_split_intensity(cfg.N, sep=28, sigma=6.0, ratio_left=ratio_left)

    open_loop = OpenLoopController(cfg.N)
    spgd = SPGDController(cfg.N, rng=np.random.default_rng(cfg.seed), delta=0.05, lr=0.4)
    tessaris = TessarisGSController(cfg.N, max_phase_step=0.5, inner_iters=8, roi_weight=0.95)

    run_open, _ = _run_one(open_loop, cfg, test_id, target_I)
    run_spgd, _ = _run_one(spgd, cfg, test_id, target_I)
    run_tess, out_dir = _run_one(tessaris, cfg, test_id, target_I)

    I_open = np.load(Path(ART_BASE) / test_id / run_open["run_hash"] / "final_intensity.npy")
    I_spgd = np.load(Path(ART_BASE) / test_id / run_spgd["run_hash"] / "final_intensity.npy")
    I_tess = np.load(Path(ART_BASE) / test_id / run_tess["run_hash"] / "final_intensity.npy")

    r_open = _split_ratio(I_open)
    r_spgd = _split_ratio(I_spgd)
    r_tess = _split_ratio(I_tess)

    err_open = abs(r_open - ratio_left)
    err_spgd = abs(r_spgd - ratio_left)
    err_tess = abs(r_tess - ratio_left)

    # Must beat baselines
    assert err_tess <= 0.5 * err_open + 1e-6, f"tessaris not beating open-loop on ratio (see {out_dir})"
    assert err_tess <= err_spgd + 1e-6, f"tessaris not beating SPGD on ratio (see {out_dir})"

    # Absolute target accuracy (start loose, tighten later)
    assert err_tess <= 0.10, f"ratio error too high: {err_tess} (see {out_dir})"
