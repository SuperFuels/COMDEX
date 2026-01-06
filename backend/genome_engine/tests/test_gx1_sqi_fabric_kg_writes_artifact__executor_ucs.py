from __future__ import annotations

import json
from pathlib import Path

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark


def test_gx1_sqi_fabric_kg_writes_artifact_executor_ucs(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TESSARIS_TEST_QUIET", "1")
    monkeypatch.setenv("TESSARIS_DETERMINISTIC_TIME", "1")

    cfg_path = Path("backend/genome_engine/examples/gx1_config_p16pilot__sqi_fabric_kgw__executor_ucs.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    # Force SQI settings
    sqi = cfg.setdefault("sqi", {})
    sqi["enabled"] = True
    sqi["level"] = "fabric"
    sqi["executor"] = "ucs"
    sqi["kg_write"] = True

    # Isolated output
    out_root = tmp_path / "P21_GX1"
    cfg["output_root"] = str(out_root)

    # Run
    run_genomics_benchmark(cfg)

    # Read run_id from disk
    latest = out_root / "runs" / "LATEST_RUN_ID.txt"
    assert latest.exists()
    run_id = latest.read_text(encoding="utf-8").strip()

    run_dir = out_root / "runs" / run_id
    rb_path = run_dir / "REPLAY_BUNDLE.json"
    assert rb_path.exists()

    rb = json.loads(rb_path.read_text(encoding="utf-8"))
    exports = ((rb.get("exports") or {}).get("sqi") or {})

    assert int(exports.get("kg_writes_count") or 0) > 0

    kg_writes_raw = Path(str(exports.get("kg_writes_path") or ""))
    assert kg_writes_raw.name == "SQI_KG_WRITES.jsonl"

    # Resolve path correctly:
    # - if exports path already includes "runs/...", it is relative to out_root
    # - if it's just "SQI_KG_WRITES.jsonl", it's relative to run_dir
    if kg_writes_raw.is_absolute():
        kg_writes_path = kg_writes_raw
    else:
        raw_s = kg_writes_raw.as_posix()
        candidates = []
        if raw_s.startswith("runs/"):
            candidates.append(out_root / kg_writes_raw)
        else:
            candidates.append(run_dir / kg_writes_raw)

        # fallback: try the other root too
        candidates.append(out_root / kg_writes_raw)
        candidates.append(run_dir / kg_writes_raw)

        kg_writes_path = next((p for p in candidates if p.exists()), candidates[0])

    assert kg_writes_path.exists()

    # Metrics contract: read METRICS.json from disk
    metrics_path = run_dir / "METRICS.json"
    assert metrics_path.exists()

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    summary = (metrics.get("summary") or {})
    assert summary.get("sqi_executor") == "ucs"
    assert int(summary.get("sqi_fabric_job_count") or 0) > 0
    assert int(summary.get("sqi_fabric_kg_write_count") or 0) > 0