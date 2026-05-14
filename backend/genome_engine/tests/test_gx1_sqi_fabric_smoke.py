# backend/genome_engine/tests/test_gx1_sqi_fabric_smoke.py
from __future__ import annotations

from backend.genome_engine.gx1_builder import build_gx1_payload


def test_gx1_sqi_fabric_trace_smoke(tmp_path):
    cfg = {
        "schemaVersion": "GX1_CONFIG_V0",
        "objective_id": "P21_GX1_GENOMICS_BENCH_V0",
        "seed": 1337,
        "created_utc": "0000-00-00T00:00:00Z",
        "dataset_path": "/workspaces/COMDEX/docs/Artifacts/v0.4/P16/docs/P16_PILOT_PREPROCESS_OUT_SNAPSHOT.jsonl",
        "output_root": str(tmp_path / "P21_GX1_SQI_FABRIC"),
        "mode": "sle",
        "mapping_id": "GX1_MAP_V1",
        "chip_mode": "ONEHOT4",
        "sqi": {
            "enabled": True,
            "level": "fabric",
            "kg_write": False,
            "plan_scope": "run",
            "max_jobs": 0,
        },
        # keep traces small/deterministic
        "trace_mode": "sampled",
        "trace_stride": 8,
        "trace_max_events": 4096,
    }

    payload = build_gx1_payload(cfg)
    trace = payload["trace"]

    assert any(e.get("trace_kind") == "sqi_bundle" for e in trace)
    assert any(e.get("trace_kind") == "sqi_fabric_plan" for e in trace)
    assert any(e.get("trace_kind") == "sqi_fabric_result" for e in trace)