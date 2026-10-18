from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from backend.modules.aion_business.runtime.business_data_write_tracer import BusinessDataWriteTracer


def tracer(tmp_path):
    return BusinessDataWriteTracer(
        source_root=Path(__file__).resolve().parents[3],
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
        vault_roots=[tmp_path / "customer-vault"],
        path_fingerprint_key=b"fingerprint-secret" * 2,
    )


def _write_text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def test_runtime_trace_classifies_writes_without_raw_paths_or_values(tmp_path):
    service = tracer(tmp_path)
    with service:
        _write_text(tmp_path / "customer-vault" / "records" / "private-customer-name.json", "secret value")
        _write_text(tmp_path / "app" / "legacy-private-customer-name.json", "secret value")
    report = service.report(session_id="crm-1", scenario="crm-customer-creation")
    encoded = json.dumps(report)
    assert report["destination_counts"]["business_vault"] >= 1
    assert report["destination_counts"]["application_boundary"] >= 1
    assert report["unsafe_write_count"] >= 1
    assert report["release_gate_passed"] is False
    assert "private-customer-name" not in encoded
    assert "secret value" not in encoded
    assert report["events"][0]["source_path"].endswith("test_business_data_write_tracer.py")


def test_reads_are_not_recorded_but_sqlite_and_mutations_are(tmp_path):
    service = tracer(tmp_path)
    existing = tmp_path / "customer-vault" / "existing.txt"
    _write_text(existing, "existing")
    with service:
        existing.read_text(encoding="utf-8")
        database = tmp_path / "customer-vault" / "records" / "guardian.sqlite3"
        database.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE example (id INTEGER)")
        existing.unlink()
    operations = {event["operation"] for event in service.report(session_id="s", scenario="x")["events"]}
    assert "sqlite.connect" in operations
    assert "os.remove" in operations
    assert "file.open_read" not in operations


def test_report_write_does_not_trace_itself(tmp_path):
    service = tracer(tmp_path)
    with service:
        _write_text(tmp_path / "customer-vault" / "a.txt", "one")
        before = service.report(session_id="s", scenario="x")["event_count"]
        service.write_report(tmp_path / "evidence" / "trace.json", session_id="s", scenario="x")
        after = service.report(session_id="s", scenario="x")["event_count"]
    assert before == after
    assert json.loads((tmp_path / "evidence" / "trace.json").read_text())["complete"] is True


def test_engineering_evidence_root_is_ignored_without_approving_other_external_writes(tmp_path):
    service = BusinessDataWriteTracer(
        source_root=Path(__file__).resolve().parents[3],
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
        vault_roots=[tmp_path / "customer-vault"],
        excluded_roots=[tmp_path / "evidence"],
        path_fingerprint_key=b"fingerprint-secret" * 2,
    )
    with service:
        _write_text(tmp_path / "evidence" / "provider-receipt.json", "content-free evidence")
        _write_text(tmp_path / "elsewhere" / "customer.json", "private")
    report = service.report(session_id="s", scenario="evidence-exclusion")
    assert report["destination_counts"] == {"external_or_unknown": 2}
    assert report["unsafe_write_count"] == 2
    assert report["release_gate_passed"] is False


def test_event_limit_fails_report_completeness(tmp_path):
    service = BusinessDataWriteTracer(
        source_root=Path(__file__).resolve().parents[3],
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
        vault_roots=[tmp_path / "customer-vault"],
        path_fingerprint_key=b"fingerprint-secret" * 2,
        max_events=1,
    )
    with service:
        _write_text(tmp_path / "app" / "one.txt", "1")
        _write_text(tmp_path / "app" / "two.txt", "2")
    report = service.report(session_id="s", scenario="x")
    assert report["complete"] is False
    assert report["dropped_event_count"] > 0


def test_failed_scenario_cannot_pass_even_when_all_writes_are_in_vault(tmp_path):
    service = tracer(tmp_path)
    with service:
        _write_text(tmp_path / "customer-vault" / "safe.txt", "safe")
    report = service.report(session_id="s", scenario="failed", scenario_completed=False)
    assert report["scenario_completed"] is False
    assert report["complete"] is False
    assert report["release_gate_passed"] is False


def test_trace_records_registered_domain_ids_without_business_identifiers(tmp_path):
    service = tracer(tmp_path)
    with service:
        sys.audit("tessaris.vault_domain_access", "business.identity", "put")
        _write_text(tmp_path / "customer-vault" / "safe.txt", "private payload")
    report = service.report(session_id="s", scenario="domain-coverage")
    encoded = json.dumps(report)
    assert report["observed_vault_domains"] == ["business.identity"]
    assert report["vault_domain_operations"] == [
        {"domain_id": "business.identity", "operation": "put", "count": 1}
    ]
    assert report["vault_domain_source_operations"] == [
        {
            "domain_id": "business.identity",
            "operation": "put",
            "source_path": "backend/tests/aion_business/test_business_data_write_tracer.py",
            "line": report["vault_domain_source_operations"][0]["line"],
            "count": 1,
        }
    ]
    assert "private payload" not in encoded


def test_explicit_secret_store_is_safe_but_other_external_paths_fail_closed(tmp_path):
    service = BusinessDataWriteTracer(
        source_root=Path(__file__).resolve().parents[3],
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
        vault_roots=[tmp_path / "customer-vault"],
        secret_store_roots=[tmp_path / "security"],
        path_fingerprint_key=b"fingerprint-secret" * 2,
    )
    with service:
        _write_text(tmp_path / "security" / "desktop-session.key", "secret")
    report = service.report(session_id="identity-access", scenario="identity")
    assert report["destination_counts"] == {"secret_store": 2}
    assert report["unsafe_write_count"] == 0
    assert report["release_gate_passed"] is True

    unsafe = BusinessDataWriteTracer(
        source_root=Path(__file__).resolve().parents[3],
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
        vault_roots=[tmp_path / "customer-vault"],
        secret_store_roots=[tmp_path / "security"],
        path_fingerprint_key=b"fingerprint-secret" * 2,
    )
    with unsafe:
        _write_text(tmp_path / "unclassified" / "record.json", "private")
    assert unsafe.report(
        session_id="identity-access", scenario="identity"
    )["release_gate_passed"] is False
