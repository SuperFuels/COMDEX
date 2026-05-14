import os
import pytest

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark


@pytest.mark.skipif(
    os.getenv("TESSARIS_RUN_UCS_TESTS") != "1",
    reason="UCS executor tests are opt-in (set TESSARIS_RUN_UCS_TESTS=1).",
)
def test_gx1_sqi_executor_ucs_smoke(tmp_path):
    cfg = {
        "schemaVersion": "GX1_CONFIG_V0",
        "objective_id": "P21_GX1_GENOMICS_BENCH_V0",
        "seed": 1337,
        "created_utc": "0000-00-00T00:00:00Z",
        "mapping_id": "GX1_MAP_V1",
        "chip_mode": "ONEHOT4",
        "dt": 0.01,
        "steps": 256,
        "mode": "sle",
        "dataset_path": "backend/genome_engine/examples/data/p16_pilot_dataset.json",
        "output_root": str(tmp_path / "P21_GX1"),
        "scenarios": [],
        "thresholds": {
            "warmup_ticks": 16,
            "eval_ticks": 32,
            "rho_matched_min": 0.0,
            "rho_mismatch_abs_max": 1.0,
            "crosstalk_max": 1.0,
            "coherence_mean_min": 0.0,
            "drift_mean_max": 1.0,
        },
        "sqi": {
            "enabled": True,
            "level": "fabric",
            "executor": "ucs",
            "kg_write": True,
            "plan_scope": "run",
            "max_jobs": 0,
        },
    }

    r = run_genomics_benchmark(cfg)
    assert r["status"] in ("OK", "FAIL")
