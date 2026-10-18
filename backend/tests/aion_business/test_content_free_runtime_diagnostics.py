from __future__ import annotations

import csv
import json
from pathlib import Path

from backend.devtools import generate_resonance_trends
from backend.modules.aion_business.runtime.content_free_diagnostics import (
    append_diagnostic_event,
    default_node_diagnostics_root,
)
from backend.system import bootstrap_diagnostics
from backend.utils.deprecation_logger import log_deprecation


def test_cross_platform_diagnostics_live_below_external_node_state():
    darwin = default_node_diagnostics_root(
        system="darwin", environment={"HOME": "/Users/founder"}
    )
    windows = default_node_diagnostics_root(
        system="windows",
        environment={
            "ProgramFiles": r"C:\Program Files",
            "ProgramData": r"C:\ProgramData",
            "LOCALAPPDATA": r"C:\Users\Founder\AppData\Local",
        },
    )
    linux = default_node_diagnostics_root(
        system="linux", environment={"HOME": "/home/founder"}
    )

    assert str(darwin).endswith("Tessaris Node/diagnostics")
    assert str(windows).replace("\\", "/").endswith("Tessaris Node/diagnostics")
    assert str(linux).endswith("/var/lib/tessaris-node/diagnostics")


def test_bootstrap_status_retains_no_source_paths_or_file_metadata(tmp_path, monkeypatch):
    private_source = tmp_path / "customer-name" / "private-state.json"
    private_source.parent.mkdir()
    private_source.write_text("private business value", encoding="utf-8")
    missing = tmp_path / "customer-name" / "missing.json"
    monkeypatch.setattr(
        bootstrap_diagnostics,
        "MODULES",
        {"PresentModule": str(private_source), "MissingModule": str(missing)},
    )
    destination = tmp_path / "node-state" / "diagnostics" / "bootstrap-status.json"

    report = bootstrap_diagnostics.build_bootstrap_map(output_path=destination)
    encoded = destination.read_text(encoding="utf-8")

    assert report["modules"]["PresentModule"] == {"status": "available"}
    assert report["modules"]["MissingModule"] == {"status": "missing"}
    assert report["content_free"] is True
    assert str(private_source) not in encoded
    assert "private-state.json" not in encoded
    assert "private business value" not in encoded
    assert "timestamp" not in encoded
    assert "size" not in encoded


def test_deprecation_log_persists_fingerprints_not_message_or_path(tmp_path):
    destination = tmp_path / "node-state" / "diagnostics" / "deprecation-events.jsonl"
    raw_message = "Customer Acme field is deprecated"
    raw_path = "/private/customer/acme_module.py"

    event = log_deprecation(
        raw_message,
        category=DeprecationWarning,
        filename=raw_path,
        lineno=42,
        log_path=destination,
    )
    encoded = destination.read_text(encoding="utf-8")
    persisted = json.loads(encoded)

    assert event == persisted
    assert persisted["content_free"] is True
    assert persisted["code"] == "DeprecationWarning"
    assert persisted["line"] == 42
    assert len(persisted["source_fingerprint"]) == 64
    assert len(persisted["detail_fingerprint"]) == 64
    assert raw_message not in encoded
    assert raw_path not in encoded


def test_diagnostic_stream_rotates_at_a_bounded_size(tmp_path):
    destination = tmp_path / "node-state" / "diagnostics" / "events.jsonl"
    kwargs = {
        "event_type": "test",
        "code": "content_free",
        "source_fingerprint": "a" * 64,
        "detail_fingerprint": "b" * 64,
        "line": 1,
        "max_bytes": 700,
    }

    append_diagnostic_event(destination, **kwargs)
    append_diagnostic_event(destination, **kwargs)
    append_diagnostic_event(destination, **kwargs)

    rotated = destination.with_suffix(".jsonl.1")
    assert destination.is_file()
    assert rotated.is_file()
    assert destination.stat().st_size <= 700
    assert rotated.stat().st_size <= 700
    assert len(list(destination.parent.glob("events.jsonl*"))) == 2


def test_synthetic_resonance_fixture_is_external_atomic_and_deterministic(
    tmp_path, monkeypatch
):
    diagnostics_root = tmp_path / "external-node-state" / "diagnostics"
    monkeypatch.setattr(
        generate_resonance_trends,
        "default_node_diagnostics_root",
        lambda: diagnostics_root,
    )

    first = generate_resonance_trends.generate_resonance_trends(
        points=3, seed=7, start_time=1000.0
    )
    first_bytes = first.read_bytes()
    second = generate_resonance_trends.generate_resonance_trends(
        points=3, seed=7, start_time=1000.0
    )

    assert first == diagnostics_root / "synthetic" / "resonance-trends.csv"
    assert second.read_bytes() == first_bytes
    with second.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [float(row["ts"]) for row in rows] == [1000.0, 1060.0, 1120.0]
    assert len(rows) == 3
    assert not list(second.parent.glob(f".{second.name}.*"))
