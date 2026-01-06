from __future__ import annotations

import json
from pathlib import Path

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark


DATA_P16_CANON = "/workspaces/COMDEX/docs/Artifacts/v0.4/P16/docs/P16_PILOT_PREPROCESS_OUT_SNAPSHOT.jsonl"


def test_trace_contract_small_and_kinds(tmp_path: Path) -> None:
    out_root = tmp_path / "P21_GX1"
    cfg = {
        "schemaVersion": "GX1_CONFIG_V0",
        "objective_id": "P21_GX1_GENOMICS_BENCH_V0",
        "seed": 1337,
        "created_utc": "0000-00-00T00:00:00Z",
        "dataset_path": DATA_P16_CANON,
        "output_root": str(out_root),
        "run_id": "P21_GX1_TRACE_CONTRACT_TEST",
        "mapping_id": "GX1_MAP_V1",
        "chip_mode": "ONEHOT4",
    }
    r = run_genomics_benchmark(cfg)
    run_dir = Path(r["run_dir"])

    lines = (run_dir / "TRACE.jsonl").read_text(encoding="utf-8").splitlines()
    # TRACE is intentionally small in this test fixture.
    # Current contract: per scenario we emit:
    #   - scenario_summary
    #   - rho_trace_eval_window
    # Plus optional integration lines:
    #   - beam_event (SLE mode)
    #   - sqi_bundle (when SQI export is enabled)
    assert 1 <= len(lines) <= 64

    allowed = {"beam_event", "scenario_summary", "rho_trace_eval_window", "sqi_bundle"}
    for ln in lines:
        ev = json.loads(ln)
        assert ev.get("trace_kind") in allowed, ev