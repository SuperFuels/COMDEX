from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark


def _load_schema(name: str) -> dict:
    p = Path("/workspaces/COMDEX/schemas") / name
    return json.loads(p.read_text(encoding="utf-8"))


def test_gx1_trace_schema_and_size(tmp_path: Path) -> None:
    dataset_path = "/workspaces/COMDEX/docs/Artifacts/v0.4/P16/docs/P16_PILOT_PREPROCESS_OUT_SNAPSHOT.jsonl"

    cfg = {
        "schemaVersion": "GX1_CONFIG_V0",
        "objective_id": "P21_GX1_GENOMICS_BENCH_V0",
        "seed": 1337,
        "created_utc": "0000-00-00T00:00:00Z",
        "dataset_path": dataset_path,
        "output_root": str(tmp_path / "P21_GX1_TRACE_CAP"),
        # Force a small trace for test
        "trace_mode": "sampled",
        "trace_stride": 16,
        "trace_max_events": 256,
    }

    r = run_genomics_benchmark(cfg)
    run_dir = Path(r["run_dir"])
    trace_path = run_dir / "TRACE.jsonl"
    assert trace_path.exists()

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert 1 <= len(lines) <= 256

    schema = _load_schema("gx1_trace_event.schema.json")
    v = jsonschema.Draft202012Validator(schema)

    # Validate all lines (bounded by max_events so it's cheap)
    for ln in lines:
        obj = json.loads(ln)
        v.validate(obj)
