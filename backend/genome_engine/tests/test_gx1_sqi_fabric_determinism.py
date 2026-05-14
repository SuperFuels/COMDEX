# backend/genome_engine/tests/test_gx1_sqi_fabric_determinism.py
from __future__ import annotations

from backend.genome_engine.gx1_builder import build_gx1_payload


def _run_once(tmp_path):
    cfg = {
        "schemaVersion": "GX1_CONFIG_V0",
        "objective_id": "P21_GX1_GENOMICS_BENCH_V0",
        "seed": 1337,
        "created_utc": "0000-00-00T00:00:00Z",
        "dataset_path": "/workspaces/COMDEX/docs/Artifacts/v0.4/P16/docs/P16_PILOT_PREPROCESS_OUT_SNAPSHOT.jsonl",
        "output_root": str(tmp_path),
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
        "trace_mode": "sampled",
        "trace_stride": 8,
        "trace_max_events": 4096,
    }
    return build_gx1_payload(cfg)


def test_gx1_sqi_fabric_determinism_same_cfg_same_digests(tmp_path):
    r1 = _run_once(tmp_path / "a")
    r2 = _run_once(tmp_path / "b")

    # Trace digest must match (bundle computed from stable_stringify(trace))
    assert r1["replay_bundle"]["trace_digest"] == r2["replay_bundle"]["trace_digest"]

    # SQI-only digest must also match (exports.sqi.sqi_digest)
    e1 = (r1["replay_bundle"].get("exports") or {}).get("sqi") or {}
    e2 = (r2["replay_bundle"].get("exports") or {}).get("sqi") or {}
    assert e1.get("sqi_digest") == e2.get("sqi_digest")