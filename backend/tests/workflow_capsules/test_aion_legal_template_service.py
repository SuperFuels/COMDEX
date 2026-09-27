from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_business.runtime.legal_template_service import (
    LegalTemplateError,
    LegalTemplateService,
)


NOW = datetime(2026, 9, 26, 18, 0, tzinfo=timezone.utc)


def _service(tmp_path):
    return LegalTemplateService(tmp_path / "legal-templates", clock=lambda: NOW)


def _draft(service, workspace="workspace-a", source=""):
    return service.create_draft(
        workspace,
        title="Customer services agreement",
        template_type="CUSTOMER_AGREEMENT",
        jurisdiction={
            "country_code": "IE", "region": "", "governing_law": "Laws of Ireland",
            "owner_confirmed": True,
        },
        content="Agreement between {{BUSINESS_NAME}} and {{CUSTOMER_NAME}}.",
        intended_use="Owner-controlled customer engagements.",
        actor_id="owner-1",
        source_template_id=source,
    )


def _approve(service, template):
    return service.approve(
        template["workspace_id"], template["template_id"], actor_id="owner-1",
        expected_content_sha256=template["content_sha256"], reviewer_name="Reviewer Name",
        reviewer_qualification="Solicitor authorised in Ireland",
        review_scope="Reviewed this exact version for the stated intended use.",
        approved_jurisdiction="Ireland", acknowledge_qualified_review=True,
    )


def test_draft_is_encrypted_workspace_isolated_and_not_presented_as_approved(tmp_path):
    service = _service(tmp_path)
    draft = _draft(service)
    assert draft["status"] == "DRAFT_REQUIRES_QUALIFIED_REVIEW"
    assert draft["variables"] == ["BUSINESS_NAME", "CUSTOMER_NAME"]
    assert draft["immutable_approved_version"] is False
    encrypted = (service.root / "workspace-a" / f"{draft['template_id']}.enc").read_text()
    assert "Agreement between" not in encrypted
    with pytest.raises(LegalTemplateError, match="template_not_found"):
        service.get_template("workspace-b", draft["template_id"])


def test_approval_requires_exact_hash_and_qualified_reviewer_assertion(tmp_path):
    service = _service(tmp_path)
    draft = _draft(service)
    with pytest.raises(LegalTemplateError, match="qualified_review_acknowledgement_required"):
        service.approve(
            "workspace-a", draft["template_id"], actor_id="owner-1",
            expected_content_sha256=draft["content_sha256"], reviewer_name="Reviewer",
            reviewer_qualification="Solicitor", review_scope="Exact version",
            approved_jurisdiction="Ireland", acknowledge_qualified_review=False,
        )
    with pytest.raises(LegalTemplateError, match="template_approval_hash_mismatch"):
        service.approve(
            "workspace-a", draft["template_id"], actor_id="owner-1",
            expected_content_sha256="0" * 64, reviewer_name="Reviewer",
            reviewer_qualification="Solicitor", review_scope="Exact version",
            approved_jurisdiction="Ireland", acknowledge_qualified_review=True,
        )
    approved = _approve(service, draft)
    assert approved["status"] == "APPROVED_FOR_CONTROLLED_USE"
    assert approved["approval"]["content_sha256"] == draft["content_sha256"]
    assert approved["approval"]["tessaris_legal_approval_claim"] is False
    with pytest.raises(LegalTemplateError, match="template_not_approvable"):
        _approve(service, approved)


def test_only_approved_exact_version_can_create_a_controlled_draft(tmp_path):
    service = _service(tmp_path)
    draft = _draft(service)
    with pytest.raises(LegalTemplateError, match="only_approved"):
        service.instantiate(
            "workspace-a", draft["template_id"], actor_id="owner-1",
            values={"BUSINESS_NAME": "Tessaris", "CUSTOMER_NAME": "Customer"},
        )
    approved = _approve(service, draft)
    with pytest.raises(LegalTemplateError, match="required_template_variable_missing:CUSTOMER_NAME"):
        service.instantiate(
            "workspace-a", approved["template_id"], actor_id="owner-1",
            values={"BUSINESS_NAME": "Tessaris"},
        )
    with pytest.raises(LegalTemplateError, match="unknown_template_variable"):
        service.instantiate(
            "workspace-a", approved["template_id"], actor_id="owner-1",
            values={"BUSINESS_NAME": "Tessaris", "CUSTOMER_NAME": "Customer", "EXTRA": "x"},
        )
    instance = service.instantiate(
        "workspace-a", approved["template_id"], actor_id="owner-1",
        values={"BUSINESS_NAME": "Tessaris", "CUSTOMER_NAME": "Customer"},
    )
    assert instance["rendered_content"] == "Agreement between Tessaris and Customer."
    assert instance["status"] == "CONTROLLED_DRAFT_REQUIRES_FINAL_HUMAN_REVIEW"
    assert instance["external_delivery_authorized"] is False


def test_approved_revision_supersedes_but_does_not_mutate_previous_version(tmp_path):
    service = _service(tmp_path)
    first = _approve(service, _draft(service))
    revision = service.create_draft(
        "workspace-a", title="Customer services agreement", template_type="CUSTOMER_AGREEMENT",
        jurisdiction={"country_code": "IE", "governing_law": "Laws of Ireland", "owner_confirmed": True},
        content="Updated agreement for {{BUSINESS_NAME}} and {{CUSTOMER_NAME}}.",
        intended_use="Owner-controlled customer engagements.", actor_id="owner-1",
        source_template_id=first["template_id"],
    )
    assert revision["version"] == 2
    assert service.get_template("workspace-a", first["template_id"])["status"] == "APPROVED_FOR_CONTROLLED_USE"
    second = _approve(service, revision)
    previous = service.get_template("workspace-a", first["template_id"])
    assert previous["status"] == "SUPERSEDED"
    assert previous["superseded_by_template_id"] == second["template_id"]
    assert previous["content_sha256"] == first["content_sha256"]
    with pytest.raises(LegalTemplateError, match="only_approved"):
        service.instantiate(
            "workspace-a", first["template_id"], actor_id="owner-1",
            values={"BUSINESS_NAME": "Tessaris", "CUSTOMER_NAME": "Customer"},
        )


def test_template_type_catalog_covers_remaining_product_workflows_without_shipping_wording(tmp_path):
    assert {
        "CUSTOMER_AGREEMENT", "SUPPLIER_AGREEMENT", "CONTRACTOR_AGREEMENT",
        "EMPLOYMENT_DOCUMENT", "TERMS_AND_CONDITIONS", "PRIVACY_NOTICE",
        "DATA_PROCESSING_AGREEMENT",
    } <= LegalTemplateService.TEMPLATE_TYPES
    assert _service(tmp_path).list_templates("workspace-a") == []


def test_scheduled_review_expiry_fails_closed_and_renewal_restores_exact_version(tmp_path):
    current = {"now": NOW}
    service = LegalTemplateService(
        tmp_path / "legal-templates", clock=lambda: current["now"],
    )
    draft = _draft(service)
    approved = service.approve(
        "workspace-a", draft["template_id"], actor_id="owner-1",
        expected_content_sha256=draft["content_sha256"], reviewer_name="Reviewer Name",
        reviewer_qualification="Solicitor authorised in Ireland",
        review_scope="Reviewed this exact version for controlled use.",
        approved_jurisdiction="Ireland", acknowledge_qualified_review=True,
        review_interval_days=30,
    )
    assert approved["approval"]["review_due_at"] == "2026-10-26T18:00:00Z"
    current["now"] = NOW + timedelta(days=31)

    with pytest.raises(LegalTemplateError, match="only_approved"):
        service.instantiate(
            "workspace-a", approved["template_id"], actor_id="owner-1",
            values={"BUSINESS_NAME": "Tessaris", "CUSTOMER_NAME": "Customer"},
        )
    overdue = service.get_template("workspace-a", approved["template_id"])
    assert overdue["status"] == "REVIEW_OVERDUE_REQUIRES_QUALIFIED_REVIEW"
    assert overdue["withdrawal"]["legal_change_reference"] == "scheduled-review-policy"
    assert overdue["content_sha256"] == approved["content_sha256"]

    renewed = service.renew_review(
        "workspace-a", approved["template_id"], actor_id="owner-1",
        expected_content_sha256=approved["content_sha256"], reviewer_name="Second Reviewer",
        reviewer_qualification="Solicitor authorised in Ireland",
        review_scope="Scheduled review of the unchanged exact version.",
        approved_jurisdiction="Ireland", acknowledge_qualified_review=True,
        review_interval_days=180,
    )
    assert renewed["status"] == "APPROVED_FOR_CONTROLLED_USE"
    assert len(renewed["approval_history"]) == 2
    assert renewed["approval"]["reviewer_name"] == "Second Reviewer"
    instance = service.instantiate(
        "workspace-a", approved["template_id"], actor_id="owner-1",
        values={"BUSINESS_NAME": "Tessaris", "CUSTOMER_NAME": "Customer"},
    )
    assert instance["template_review_due_at"] == renewed["approval"]["review_due_at"]


def test_legal_change_withdrawal_stops_new_use_without_rewriting_history(tmp_path):
    service = _service(tmp_path)
    approved = _approve(service, _draft(service))
    with pytest.raises(LegalTemplateError, match="acknowledgement"):
        service.withdraw_for_legal_change(
            "workspace-a", approved["template_id"], actor_id="owner-1",
            reason="Regulator published new mandatory wording",
            legal_change_reference="regulator-notice-2026-09", acknowledge_withdrawal=False,
        )
    withdrawn = service.withdraw_for_legal_change(
        "workspace-a", approved["template_id"], actor_id="owner-1",
        reason="Regulator published new mandatory wording",
        legal_change_reference="regulator-notice-2026-09", acknowledge_withdrawal=True,
    )
    assert withdrawn["status"] == "WITHDRAWN_FOR_LEGAL_CHANGE"
    assert withdrawn["withdrawal"]["content_sha256"] == approved["content_sha256"]
    assert withdrawn["immutable_approved_version"] is True
    assert withdrawn["approval_history"][0]["approval_id"] == approved["approval"]["approval_id"]
    with pytest.raises(LegalTemplateError, match="only_approved"):
        service.instantiate(
            "workspace-a", approved["template_id"], actor_id="owner-1",
            values={"BUSINESS_NAME": "Tessaris", "CUSTOMER_NAME": "Customer"},
        )


def test_review_schedule_sweep_is_workspace_scoped_and_idempotent(tmp_path):
    current = {"now": NOW}
    service = LegalTemplateService(tmp_path / "legal-templates", clock=lambda: current["now"])
    first = _approve(service, _draft(service, workspace="workspace-a"))
    second = _approve(service, _draft(service, workspace="workspace-b"))
    current["now"] = NOW + timedelta(days=366)
    result = service.enforce_review_schedule("workspace-a", actor_id="legal-owner")
    assert result["checked"] == 1
    assert result["withdrawn_for_overdue_review"] == 1
    assert service.get_template("workspace-a", first["template_id"])["status"] == "REVIEW_OVERDUE_REQUIRES_QUALIFIED_REVIEW"
    assert service._load("workspace-b", second["template_id"])["status"] == "APPROVED_FOR_CONTROLLED_USE"
    assert service.list_templates("workspace-b")[0]["status"] == "REVIEW_OVERDUE_REQUIRES_QUALIFIED_REVIEW"
    assert service.enforce_review_schedule("workspace-a")["withdrawn_for_overdue_review"] == 0
