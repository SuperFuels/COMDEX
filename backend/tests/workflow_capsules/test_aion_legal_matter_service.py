from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from backend.modules.aion_business.runtime.legal_matter_service import LegalMatterError, LegalMatterService


NOW = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)


def _service(tmp_path):
    return LegalMatterService(tmp_path / "legal-matters", clock=lambda: NOW)


def _jurisdiction():
    return {
        "country_code": "IE",
        "region": "Dublin",
        "governing_law": "Law of Ireland",
        "forum": "Courts of Ireland",
        "owner_confirmed": True,
    }


def test_matter_is_persisted_with_structured_triage_and_jurisdiction(tmp_path):
    service = _service(tmp_path)
    matter = service.create_matter(
        "workspace-a",
        title="Supplier contract review",
        counterparty="Example Supplier",
        matter_type="contract",
        risk="high",
        summary="Renewal terms need review.",
        jurisdiction=_jurisdiction(),
        actor_id="owner-1",
    )

    assert matter["status"] == "OPEN"
    assert matter["risk"] == "HIGH"
    assert matter["jurisdiction"]["country_code"] == "IE"
    assert matter["jurisdiction"]["owner_confirmed"] is True
    assert service.verify_audit_chain("workspace-a", matter["matter_id"])
    assert service.list_matters("workspace-a")[0]["matter_id"] == matter["matter_id"]


def test_workspace_isolation_prevents_cross_workspace_reads(tmp_path):
    service = _service(tmp_path)
    matter = service.create_matter(
        "workspace-a", title="Private matter", counterparty="", matter_type="DISPUTE",
        risk="NORMAL", summary="", jurisdiction=_jurisdiction(), actor_id="owner-1",
    )
    with pytest.raises(LegalMatterError, match="matter_not_found"):
        service.get_matter("workspace-b", matter["matter_id"])


def test_jurisdiction_requires_explicit_owner_confirmation(tmp_path):
    service = _service(tmp_path)
    jurisdiction = _jurisdiction()
    jurisdiction["owner_confirmed"] = False
    with pytest.raises(LegalMatterError, match="jurisdiction_owner_confirmation_required"):
        service.create_matter(
            "workspace-a", title="Matter", counterparty="", matter_type="PRIVACY",
            risk="NORMAL", summary="", jurisdiction=jurisdiction, actor_id="owner-1",
        )


def test_triage_is_audited_and_does_not_rewrite_prior_event(tmp_path):
    service = _service(tmp_path)
    matter = service.create_matter(
        "workspace-a", title="Complaint", counterparty="Customer", matter_type="COMPLAINT",
        risk="NORMAL", summary="Initial facts", jurisdiction=_jurisdiction(), actor_id="owner-1",
    )
    first_hash = matter["audit_events"][0]["event_hash"]
    updated = service.triage_matter(
        "workspace-a", matter["matter_id"], actor_id="owner-1",
        risk="URGENT", status="ON_HOLD", summary="Awaiting external counsel.",
    )
    assert updated["risk"] == "URGENT"
    assert updated["status"] == "ON_HOLD"
    assert updated["audit_events"][0]["event_hash"] == first_hash
    assert updated["audit_events"][1]["previous_hash"] == first_hash
    assert service.verify_audit_chain("workspace-a", matter["matter_id"])


def test_tampered_audit_event_is_detected(tmp_path):
    service = _service(tmp_path)
    matter = service.create_matter(
        "workspace-a", title="Employment", counterparty="Worker", matter_type="EMPLOYMENT",
        risk="LOW", summary="", jurisdiction=_jurisdiction(), actor_id="owner-1",
    )
    path = service._path("workspace-a", matter["matter_id"])
    raw = service._read(path)
    raw["audit_events"][0]["detail"]["risk"] = "URGENT"
    service.store.write(path, raw, workspace_id="workspace-a", record_id=matter["matter_id"])
    assert service.verify_audit_chain("workspace-a", matter["matter_id"]) is False


def test_retention_hold_export_and_guarded_deletion(tmp_path):
    service = _service(tmp_path)
    matter = service.create_matter(
        "workspace-a", title="Closed dispute", counterparty="Customer", matter_type="DISPUTE",
        risk="NORMAL", summary="Private case facts", jurisdiction=_jurisdiction(), actor_id="owner-1",
    )
    matter_id = matter["matter_id"]
    service.triage_matter("workspace-a", matter_id, actor_id="owner-1", status="CLOSED")
    held = service.update_records_governance(
        "workspace-a", matter_id, actor_id="owner-1",
        retain_until="2026-09-25T12:00:00Z", legal_hold=True,
        legal_hold_reason="Pending regulator enquiry",
    )
    assert held["records_governance"]["legal_hold"] is True
    with pytest.raises(LegalMatterError, match="legal_hold"):
        service.destroy_matter(
            "workspace-a", matter_id, actor_id="owner-1", confirmation=f"DELETE {matter_id}",
        )

    filename, exported = service.export_matter("workspace-a", matter_id, "owner-1")
    assert filename.endswith(".tessaris-legal-matter.json")
    assert json.loads(exported)["summary"] == "Private case facts"
    service.update_records_governance(
        "workspace-a", matter_id, actor_id="owner-1", legal_hold=False,
    )
    with pytest.raises(LegalMatterError, match="exact_deletion_confirmation_required"):
        service.destroy_matter(
            "workspace-a", matter_id, actor_id="owner-1", confirmation="DELETE wrong-record",
        )
    receipt = service.destroy_matter(
        "workspace-a", matter_id, actor_id="owner-1", confirmation=f"DELETE {matter_id}",
    )
    assert receipt["record_type"] == "legal_matter"
    assert len(receipt["destroyed_record_sha256"]) == 64
    assert "Private case facts" not in json.dumps(receipt)
    assert next((tmp_path / "legal-matters" / "workspace-a" / "_destruction").glob("*.enc"))
    with pytest.raises(LegalMatterError, match="matter_not_found"):
        service.get_matter("workspace-a", matter_id)


def test_matter_links_documents_communications_envelopes_and_proofs_by_reference(tmp_path):
    service = _service(tmp_path)
    matter = service.create_matter(
        "workspace-a", title="Contract negotiation", counterparty="Supplier",
        matter_type="CONTRACT", risk="NORMAL", summary="",
        jurisdiction=_jurisdiction(), actor_id="owner-1",
    )
    for kind, reference in (
        ("DOCUMENT", "document-001"),
        ("COMMUNICATION", "message-001"),
        ("SIGNATURE_ENVELOPE", "envelope-001"),
        ("PROOF_RECEIPT", "proof-001"),
    ):
        matter = service.link_record(
            "workspace-a", matter["matter_id"], actor_id="owner-1",
            record_type=kind, reference_id=reference, label=f"Linked {kind}",
            content_sha256="ab" * 32,
        )
    assert [item["record_type"] for item in matter["linked_records"]] == [
        "DOCUMENT", "COMMUNICATION", "SIGNATURE_ENVELOPE", "PROOF_RECEIPT",
    ]
    assert service.verify_audit_chain("workspace-a", matter["matter_id"])
    with pytest.raises(LegalMatterError, match="linked_record_already_exists"):
        service.link_record(
            "workspace-a", matter["matter_id"], actor_id="owner-1",
            record_type="DOCUMENT", reference_id="document-001",
        )


def test_obligation_reminders_are_due_scoped_and_stop_after_completion(tmp_path):
    service = _service(tmp_path)
    matter = service.create_matter(
        "workspace-a", title="Annual renewal", counterparty="Supplier",
        matter_type="CONTRACT", risk="HIGH", summary="",
        jurisdiction=_jurisdiction(), actor_id="owner-1",
    )
    matter = service.add_obligation(
        "workspace-a", matter["matter_id"], actor_id="owner-1",
        title="Review renewal terms", obligation_type="RENEWAL",
        due_at="2026-10-01T09:00:00Z",
        remind_at=["2026-09-25T09:00:00Z", "2026-09-29T09:00:00Z"],
        owner_id="owner-1", source_reference_id="document-001",
    )
    obligation = matter["obligations"][0]
    due = service.due_obligations("workspace-a", as_of="2026-09-26T12:00:00Z")
    assert len(due) == 1
    assert due[0]["overdue"] is False
    assert service.due_obligations("workspace-b", as_of="2026-10-02T12:00:00Z") == []
    service.update_obligation(
        "workspace-a", matter["matter_id"], obligation["obligation_id"],
        actor_id="owner-1", status="COMPLETED",
    )
    assert service.due_obligations("workspace-a", as_of="2026-10-02T12:00:00Z") == []


def test_obligation_rejects_reminder_on_or_after_due_date(tmp_path):
    service = _service(tmp_path)
    matter = service.create_matter(
        "workspace-a", title="Notice", counterparty="Customer",
        matter_type="DISPUTE", risk="NORMAL", summary="",
        jurisdiction=_jurisdiction(), actor_id="owner-1",
    )
    with pytest.raises(LegalMatterError, match="obligation_reminder_must_precede_due_date"):
        service.add_obligation(
            "workspace-a", matter["matter_id"], actor_id="owner-1",
            title="Serve notice", obligation_type="NOTICE",
            due_at="2026-10-01T09:00:00Z", remind_at=["2026-10-01T09:00:00Z"],
        )


def test_professional_escalation_is_a_draft_and_never_authorizes_external_delivery(tmp_path):
    service = _service(tmp_path)
    matter = service.create_matter(
        "workspace-a", title="Threatened claim", counterparty="Customer",
        matter_type="DISPUTE", risk="URGENT", summary="Customer threatened proceedings.",
        jurisdiction=_jurisdiction(), actor_id="owner-1",
    )
    escalated = service.create_professional_escalation(
        "workspace-a", matter["matter_id"], actor_id="owner-1",
        reason="Limitation period and response require professional review.",
        urgency="URGENT", requested_professional="Irish commercial solicitor",
    )
    escalation = escalated["professional_escalations"][0]
    assert escalation["status"] == "DRAFT_REQUIRES_HUMAN_APPROVAL"
    assert escalation["external_delivery_authorized"] is False
    assert len(escalation["matter_snapshot_sha256"]) == 64
    assert service.verify_audit_chain("workspace-a", matter["matter_id"])
