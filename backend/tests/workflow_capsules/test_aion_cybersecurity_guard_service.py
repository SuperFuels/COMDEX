from __future__ import annotations

import json
import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.cybersecurity_guard_service import (
    CommandEvidence,
    CybersecurityGuardScheduler,
    CybersecurityGuardService,
)


def service(tmp_path) -> CybersecurityGuardService:
    return CybersecurityGuardService(root=tmp_path / "guard")


def test_safe_scan_is_workspace_scoped_and_read_only(tmp_path, monkeypatch):
    guard = service(tmp_path)
    monkeypatch.setattr(guard, "_inventory", lambda: ([{
        "asset_id": "device_test", "asset_type": "desktop_or_vm", "display_name": "test-device",
        "operating_system": "TestOS", "os_release": "1", "architecture": "arm64",
        "application_count": 3, "observed_at": "2026-09-27T00:00:00+00:00", "source": "test",
    }], {
        "firewall": CommandEvidence("OK", "Firewall is disabled", "firewall-test"),
        "backup": CommandEvidence("NOT_ASSESSED", "No adapter configured", "backup-test"),
    }))

    result = guard.run_safe_scan("workspace-a", actor_id="owner")

    assert result["scan_run"]["kind"] == "SAFE_LOCAL_READ_ONLY"
    assert "no_response_action" in result["scan_run"]["boundaries"]
    assert any(item["severity"] == "HIGH" and item["category"] == "firewall" for item in result["state"]["findings"])
    assert guard.load("workspace-b")["findings"] == []
    assert guard.load("workspace-a")["workspace_id"] == "workspace-a"


def test_disruptive_action_requires_exact_approval_and_is_not_executed(tmp_path):
    guard = service(tmp_path)
    proposal = guard.propose_action(
        "workspace-a", actor_id="security_pilot", action_type="quarantine_file",
        target="attachment.bin", reason="Known-malware signature requires human review.",
    )
    assert proposal["status"] == "AWAITING_APPROVAL"
    assert proposal["execution_enabled"] is False

    with pytest.raises(PermissionError, match="exact_security_action_confirmation_required"):
        guard.approve_action("workspace-a", proposal["proposal_id"], actor_id="owner", confirmation="yes")

    approved = guard.approve_action(
        "workspace-a", proposal["proposal_id"], actor_id="owner",
        confirmation=f"APPROVE {proposal['proposal_id']}",
    )
    assert approved["status"] == "APPROVED_NOT_EXECUTED"
    assert approved["execution_enabled"] is False
    with pytest.raises(RuntimeError, match="endpoint_response_executor_not_configured"):
        guard.execute_approved_action(
            "workspace-a", proposal["proposal_id"], actor_id="owner",
            confirmation=f"EXECUTE {proposal['proposal_id']}",
        )


def test_separately_injected_response_executor_needs_second_exact_confirmation(tmp_path):
    class Executor:
        def execute(self, proposal):
            return {"ok": True, "executor": "test-reversible-adapter", "reference": proposal["proposal_id"]}

    guard = CybersecurityGuardService(root=tmp_path / "guard", response_executor=Executor())
    proposal = guard.propose_action(
        "workspace-a", actor_id="pilot", action_type="isolate_device",
        target="device_test", reason="Confirmed containment exercise",
    )
    guard.approve_action(
        "workspace-a", proposal["proposal_id"], actor_id="owner",
        confirmation=f"APPROVE {proposal['proposal_id']}",
    )
    with pytest.raises(PermissionError, match="exact_security_execution_confirmation_required"):
        guard.execute_approved_action("workspace-a", proposal["proposal_id"], actor_id="owner", confirmation="execute")
    executed = guard.execute_approved_action(
        "workspace-a", proposal["proposal_id"], actor_id="owner",
        confirmation=f"EXECUTE {proposal['proposal_id']}",
    )
    assert executed["status"] == "EXECUTED"
    assert executed["execution_receipt"]["executor"] == "test-reversible-adapter"


def test_incident_records_append_only_opening_event(tmp_path):
    guard = service(tmp_path)
    incident = guard.create_incident(
        "workspace-a", actor_id="owner", title="Suspicious supplier email",
        severity="HIGH", summary="Attachment held for local review.",
    )
    assert incident["status"] == "OPEN"
    assert incident["events"][0]["event_type"] == "OPENED"
    events = (tmp_path / "guard" / "workspace-a" / "events.jsonl").read_text().splitlines()
    assert json.loads(events[-1])["event_type"] == "INCIDENT_OPENED"


def test_investigation_uses_recorded_evidence_and_states_limit(tmp_path, monkeypatch):
    guard = service(tmp_path)
    monkeypatch.setattr(guard, "_inventory", lambda: ([{
        "asset_id": "device_test", "asset_type": "desktop_or_vm", "display_name": "test-device",
        "operating_system": "TestOS", "os_release": "1", "architecture": "arm64",
        "application_count": 0, "observed_at": "now", "source": "test",
    }], {"firewall": CommandEvidence("OK", "Firewall enabled", "test")}))
    guard.run_safe_scan("workspace-a", actor_id="owner")
    result = guard.investigate("workspace-a", question="Am I completely safe?")
    assert "not run an active network probe" in result["answer"]
    assert "deterministic_summary_not_security_certification" in result["limitations"]


def test_command_output_is_bounded_before_persistence(tmp_path, monkeypatch):
    guard = service(tmp_path)

    class Result:
        returncode = 0
        stdout = "secret-value " * 500
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Result())
    evidence = guard._command(["/usr/bin/example", "--read-only"])
    assert len(evidence.summary) <= 500
    assert evidence.source == "/usr/bin/example"


def test_vulnerability_feed_requires_configured_anchor_and_valid_signature(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    feed = {
        "schema_version": "tessaris.cybersecurity.vulnerability-feed.v1",
        "feed_id": "test-feed-1", "issued_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), "entries": [{
            "advisory_id": "TEST-2026-1", "ecosystem": "macos_application",
            "product": "Example App", "affected_versions": ["1.2.3"],
            "fixed_version": "1.2.4", "severity": "HIGH",
        }],
    }
    canonical = json.dumps(feed, sort_keys=True, separators=(",", ":")).encode()
    signature = base64.b64encode(private_key.sign(canonical)).decode()
    guard = CybersecurityGuardService(
        root=tmp_path / "guard", trusted_feed_public_key=base64.b64encode(public_key).decode(),
    )
    descriptor = guard.import_vulnerability_feed("workspace-a", actor_id="owner", feed=feed, signature_base64=signature)
    assert descriptor["signature_verified"] is True
    assert guard.load("workspace-a")["capabilities"]["vulnerability_feed"] == "SIGNED_FEED_ACTIVE"
    state = guard.load("workspace-a")
    state["assets"] = [{"asset_id": "device_test", "software": [{
        "name": "Example App", "version": "1.2.3", "ecosystem": "macos_application",
    }]}]
    guard._write("workspace-a", state)
    assessment = guard.assess_vulnerabilities("workspace-a", actor_id="owner")
    assert assessment["match_count"] == 1
    assert assessment["matches"][0]["fixed_version"] == "1.2.4"

    with pytest.raises(PermissionError, match="vulnerability_feed_signature_invalid"):
        guard.import_vulnerability_feed("workspace-a", actor_id="owner", feed=feed, signature_base64=base64.b64encode(b"x" * 64).decode())


def test_secret_scan_is_scoped_and_never_retains_secret_value(tmp_path):
    allowed = tmp_path / "approved"
    allowed.mkdir()
    secret_value = "sk-example-THIS_VALUE_MUST_NEVER_BE_STORED_123456"
    (allowed / "settings.env").write_text(f"API_KEY={secret_value}\n", encoding="utf-8")
    guard = CybersecurityGuardService(root=tmp_path / "guard", allowed_scan_roots=[allowed])
    record = guard.scan_secrets("workspace-a", actor_id="owner", scope=str(allowed))
    assert record["match_count"] >= 1
    assert all(item["value_redacted"] for item in record["matches"])
    assert all("excessive_permissions" in item for item in record["matches"])
    persisted = (tmp_path / "guard" / "workspace-a" / "state.json").read_text()
    assert secret_value not in persisted
    with pytest.raises(PermissionError, match="secret_scan_scope_not_allowed"):
        guard.scan_secrets("workspace-a", actor_id="owner", scope=str(tmp_path))


def test_attachment_analysis_is_static_and_does_not_retain_content(tmp_path):
    guard = service(tmp_path)
    content = b"harmless header powershell https://suspicious.invalid/login"
    result = guard.analyse_attachment(
        "workspace-a", actor_id="owner", filename="invoice.pdf.exe",
        media_type="application/octet-stream", data=content,
    )
    types = {item["type"] for item in result["indicators"]}
    assert {"executable_or_script", "double_extension", "active_content", "external_links"}.issubset(types)
    assert result["content_retained"] is False
    assert content.decode() not in (tmp_path / "guard" / "workspace-a" / "state.json").read_text()


def test_update_check_is_read_only_and_restore_test_is_evidence_record(tmp_path, monkeypatch):
    guard = service(tmp_path)
    monkeypatch.setattr("platform.system", lambda: "TestOS")
    update = guard.check_updates("workspace-a", actor_id="owner")
    assert update["installation_performed"] is False
    restore = guard.record_restore_test(
        "workspace-a", actor_id="owner", backup_system="Encrypted backup",
        tested_at="2026-09-27T10:00:00Z", result="PASSED", evidence_reference="test-report-17",
    )
    assert restore["result"] == "PASSED"
    assert guard.load("workspace-a")["restore_tests"][0]["evidence_reference"] == "test-report-17"


def test_domain_validation_rejects_non_domain_targets_without_network_access(tmp_path):
    guard = service(tmp_path)
    with pytest.raises(ValueError, match="invalid_domain_name"):
        guard.check_domain("workspace-a", actor_id="owner", hostname="127.0.0.1")
    with pytest.raises(ValueError, match="invalid_domain_name"):
        guard.check_domain("workspace-a", actor_id="owner", hostname="file:///etc/passwd")


def test_domain_check_rejects_dns_resolution_to_private_address(tmp_path, monkeypatch):
    guard = service(tmp_path)
    monkeypatch.setattr("socket.getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="domain_resolves_to_non_public_address"):
        guard.check_domain("workspace-a", actor_id="owner", hostname="example.com")


def test_backup_freshness_parser_is_bounded_to_supported_timestamp_shape(tmp_path):
    guard = service(tmp_path)
    assert guard._backup_age_hours("/Backups/2020-01-01-000000") is not None
    assert guard._backup_age_hours("backup succeeded but no timestamp supplied") is None


def test_backend_scheduler_scans_only_activated_workspace_records(tmp_path, monkeypatch):
    guard = service(tmp_path)
    guard.load("workspace-a")
    monkeypatch.setattr(guard, "_inventory", lambda: ([{
        "asset_id": "device_test", "asset_type": "desktop_or_vm", "display_name": "test-device",
        "operating_system": "TestOS", "os_release": "1", "architecture": "arm64",
        "application_count": 0, "software": [], "observed_at": "now", "source": "test",
    }], {"firewall": CommandEvidence("OK", "Firewall enabled", "test")}))
    results = CybersecurityGuardScheduler(guard, interval_seconds=60).run_once()
    assert results[0]["workspace_id"] == "workspace-a"
    assert results[0]["ok"] is True
    assert guard.load("workspace-a")["guard"]["last_scan_at"] is not None
