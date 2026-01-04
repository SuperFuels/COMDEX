import json
from backend.genome_engine.gx1_builder import build_gx1_payload

def test_gx1_sle_trace_contains_beam_and_legacy(tmp_path):
    cfg = {
        "schemaVersion": "GX1_CONFIG_V0",
        "objective_id": "P21_GX1_GENOMICS_BENCH_V0",
        "seed": 1337,
        "created_utc": "0000-00-00T00:00:00Z",
        "dataset_path": "/workspaces/COMDEX/docs/Artifacts/v0.4/P16/docs/P16_PILOT_PREPROCESS_OUT_SNAPSHOT.jsonl",
        "output_root": str(tmp_path / "P21_GX1_SLE"),
        "mode": "sle",
        "mapping_id": "GX1_MAP_V1",
        "chip_mode": "ONEHOT4",
    }

    payload = build_gx1_payload(cfg)
    trace = payload["trace"]
    assert any(e.get("trace_kind") == "beam_event" for e in trace)
    assert any(e.get("trace_kind") == "scenario_summary" for e in trace)
    assert any(e.get("trace_kind") == "rho_trace_eval_window" for e in trace)