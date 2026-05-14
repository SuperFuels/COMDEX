from __future__ import annotations

import json
from pathlib import Path

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark


def test_gx1_ledger_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TESSARIS_TEST_QUIET", "1")
    monkeypatch.setenv("TESSARIS_DETERMINISTIC_TIME", "1")

    cfg_path = Path("backend/genome_engine/examples/gx1_config_p16pilot__sqi_fabric_kgw__executor_ucs.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    out_root = tmp_path / "P21_GX1"
    cfg["output_root"] = str(out_root)

    # turn ledger on (schema update required if config schema is strict)
    cfg["ledger"] = {"enabled": True}

    r = run_genomics_benchmark(cfg)
    assert (r.get("metrics") or {}).get("schemaVersion") == "GX1_METRICS_V0"

    latest = out_root / "runs" / "LATEST_RUN_ID.txt"
    assert latest.exists()
    run_id = latest.read_text(encoding="utf-8").strip()

    run_dir = out_root / "runs" / run_id
    rb_path = run_dir / "REPLAY_BUNDLE.json"
    assert rb_path.exists()

    rb = json.loads(rb_path.read_text(encoding="utf-8"))
    exports = rb.get("exports") or {}

    led = (exports.get("ledger") or {})
    assert led.get("enabled") is True
    assert str(led.get("ledger_path") or "") == "LEDGER.jsonl"
    assert int(led.get("ledger_count") or 0) > 0
    assert isinstance(led.get("ledger_digest"), str) and len(str(led.get("ledger_digest"))) == 64

    ledger_path = run_dir / "LEDGER.jsonl"
    assert ledger_path.exists()
    assert ledger_path.stat().st_size > 0