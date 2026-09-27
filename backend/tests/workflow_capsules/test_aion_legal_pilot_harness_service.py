from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.modules.aion_business.runtime.legal_document_service import LegalDocumentError, LegalDocumentService
from backend.modules.aion_business.runtime.legal_matter_service import LegalMatterService
from backend.modules.aion_business.runtime.legal_pilot_harness_service import LegalPilotHarnessService


NOW = datetime(2026, 9, 26, 16, 0, tzinfo=timezone.utc)


def _harness(tmp_path):
    documents = LegalDocumentService(tmp_path / "documents", clock=lambda: NOW)
    matters = LegalMatterService(tmp_path / "matters", clock=lambda: NOW)
    return LegalPilotHarnessService(documents, matters), documents, matters


def test_harness_reviews_only_protected_workspace_document_ids(tmp_path):
    harness, documents, _ = _harness(tmp_path)
    document = documents.ingest(
        "workspace-a", filename="terms.txt", media_type="text/plain",
        content=b"AUTOMATIC RENEWAL\nThis agreement shall automatically renew and has unlimited liability.",
        actor_id="owner-1",
    )
    result = harness.handle(
        "workspace-a", "Review the attached terms", actor_id="owner-1",
        attachments=[document["document_id"]],
    )
    assert result["handled"] is True
    assert result["reliability"] == "deterministic_local_legal_harness"
    assert result["external_writes_performed"] is False
    assert result["not_legal_advice"] is True
    assert "Unlimited liability" in result["content"]
    assert result["action_receipts"][0]["capability"] == "legal.review_contract"

    with pytest.raises(LegalDocumentError, match="document_not_found"):
        harness.handle(
            "workspace-b", "Review this", actor_id="owner-2", attachments=[document["document_id"]],
        )


def test_harness_rejects_raw_paths_and_unprotected_attachment_references(tmp_path):
    harness, _, _ = _harness(tmp_path)
    with pytest.raises(ValueError, match="protected_document_ids"):
        harness.handle(
            "workspace-a", "Review this", actor_id="owner-1", attachments=["/Users/example/private-contract.pdf"],
        )


def test_harness_compares_two_exact_versions_and_keeps_external_authority_false(tmp_path):
    harness, documents, _ = _harness(tmp_path)
    first = documents.ingest(
        "workspace-a", filename="v1.txt", media_type="text/plain", content=b"Payment in 30 days.", actor_id="owner-1",
    )
    second = documents.ingest(
        "workspace-a", filename="v2.txt", media_type="text/plain", content=b"Payment in 90 days.", actor_id="owner-1",
    )
    result = harness.handle(
        "workspace-a", "Compare these versions", actor_id="owner-1",
        attachments=[first["document_id"], second["document_id"]],
    )
    assert "1 added and 1 removed" in result["content"]
    assert result["external_delivery_authorized"] is False
    assert result["action_receipts"][0]["capability"] == "legal.compare_versions"


def test_harness_reports_workspace_state_without_inventing_advice(tmp_path):
    harness, _, matters = _harness(tmp_path)
    matters.create_matter(
        "workspace-a", title="Threatened claim", counterparty="Customer", matter_type="DISPUTE",
        risk="URGENT", summary="", jurisdiction={"country_code": "IE", "region": "",
        "governing_law": "Law of Ireland", "forum": "", "owner_confirmed": True}, actor_id="owner-1",
    )
    result = harness.handle("workspace-a", "What needs attention?", actor_id="owner-1")
    assert "1 open matter" in result["content"]
    assert "1 high-priority" in result["content"]
    assert "cannot represent the business" in result["content"]
