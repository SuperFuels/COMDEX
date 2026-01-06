from __future__ import annotations

import json
from pathlib import Path

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark


def test_gx1_sqi_fabric_kg_writes_artifact() -> None:
    cfg_path = Path("backend/genome_engine/examples/gx1_config_p16pilot.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    sqi = cfg.get("sqi") if isinstance(cfg.get("sqi"), dict) else {}
    sqi.update({"enabled": True, "level": "fabric", "kg_write": True})
    cfg["sqi"] = sqi

    r = run_genomics_benchmark(cfg)

    run_dir = Path(r["run_dir"])
    kgw_path = run_dir / "SQI_KG_WRITES.jsonl"
    assert kgw_path.exists(), f"missing {kgw_path}"
    assert kgw_path.stat().st_size > 0, "SQI_KG_WRITES.jsonl is empty"

    replay = json.loads((run_dir / "REPLAY_BUNDLE.json").read_text(encoding="utf-8"))
    sqi_exp = (((replay.get("exports") or {}).get("sqi")) or {})
    assert int(sqi_exp.get("kg_writes_count", 0)) > 0
    assert isinstance(sqi_exp.get("kg_writes_digest"), str) and len(sqi_exp["kg_writes_digest"]) >= 16
    assert sqi_exp.get("kg_writes_path") == f"runs/{r['run_id']}/SQI_KG_WRITES.jsonl"

    # Optional: verify file path matches the replay-bundle pointer
    phase_root = Path(r["phase_root"])
    expected = phase_root / "runs" / r["run_id"] / "SQI_KG_WRITES.jsonl"
    assert expected.resolve() == kgw_path.resolve()