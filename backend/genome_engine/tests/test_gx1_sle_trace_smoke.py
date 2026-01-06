from __future__ import annotations

from backend.genome_engine.gx1_builder import build_gx1_payload


def test_gx1_sle_trace_contains_beam_legacy_and_sqi_bundle(tmp_path) -> None:
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

        # Contract: when enabled, SLE/Mode B emits sqi_bundle records into TRACE.
        # Keep legacy flag for back-compat with earlier configs/tests.
        "export_sqi_bundle": True,
        # Also accept the pipeline form (if present in builder defaults / callers).
        "sqi": {"enabled": True, "level": "bundle"},
    }

    payload = build_gx1_payload(cfg)
    trace = payload["trace"]

    # SLE normalized + legacy contract lines
    assert any(e.get("trace_kind") == "beam_event" for e in trace)
    assert any(e.get("trace_kind") == "scenario_summary" for e in trace)
    assert any(e.get("trace_kind") == "rho_trace_eval_window" for e in trace)

    # New contract surface
    assert any(e.get("trace_kind") == "sqi_bundle" for e in trace)