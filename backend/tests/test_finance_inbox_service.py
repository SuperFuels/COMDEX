from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_inbox_service import FinanceInboxService
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _services(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", runtime)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", runtime / "business_containers")
    monkeypatch.setattr(AIONBusinessPaths, "AUDIT", runtime / "audit")
    repository = BusinessContainerRepository(runtime / "business_containers")
    authority = OrganizationAuthorityService(repository)
    model = authority.empty("acme")
    model["departments"] = [
        {"id": "department.executive", "name": "Leadership", "status": "active"},
        {"id": "department.operations", "name": "Operations", "status": "active", "parent_department_id": "department.executive"},
    ]
    model["people"] = [
        {"id": "person.owner", "name": "Alex Owner", "email": "owner@acme.test", "employment_type": "owner", "status": "active", "department_ids": ["department.executive"], "role_ids": ["role.owner_director"]},
        {"id": "person.worker", "name": "Sam Worker", "email": "sam@acme.test", "employment_type": "employee", "status": "active", "manager_id": "person.owner", "department_ids": ["department.operations"], "project_ids": ["project.installation-1"], "role_ids": ["role.employee"]},
    ]
    model["assets"] = [
        {"id": "asset.worker-card", "name": "Sam's card", "asset_type": "company_card", "assigned_person_id": "person.worker", "last_four": "1234", "transaction_limit": 250},
        {"id": "asset.owner-card", "name": "Owner card", "asset_type": "company_card", "assigned_person_id": "person.owner", "last_four": "9999"},
    ]
    authority.save("acme", model)
    return FinanceInboxService(repository), authority


def test_image_upload_is_hash_bound_linked_and_deduplicated(tmp_path, monkeypatch):
    service, _ = _services(tmp_path, monkeypatch)
    document, duplicate = service.ingest(
        "acme", filename="phone receipt.jpg", content=b"jpeg-test-bytes", mime_type="image/jpeg",
        submitted_by_person_id="person.worker", card_asset_id="asset.worker-card",
    )
    assert duplicate is False
    assert document["status"] == "needs_review"
    assert document["source"]["channel"] == "desktop_upload"
    assert document["source"]["preview_kind"] == "image"
    assert document["ownership"]["department_id"] == "department.operations"
    assert document["ownership"]["project_id"] == "project.installation-1"
    assert document["authority"]["submission"]["allowed"] is True
    assert service.file_path("acme", document["id"])[0].read_bytes() == b"jpeg-test-bytes"
    repeated, duplicate = service.ingest(
        "acme", filename="renamed.jpg", content=b"jpeg-test-bytes", mime_type="image/jpeg",
        submitted_by_person_id="person.worker",
    )
    assert duplicate is True
    assert repeated["id"] == document["id"]
    assert service.get("acme")["summary"]["total_documents"] == 1


def test_card_owned_by_another_person_is_rejected(tmp_path, monkeypatch):
    service, _ = _services(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="card_assigned_to_another_person"):
        service.ingest(
            "acme", filename="receipt.png", content=b"png", mime_type="image/png",
            submitted_by_person_id="person.worker", card_asset_id="asset.owner-card",
        )


def test_review_routes_to_authorised_manager_and_prepares_no_external_write(tmp_path, monkeypatch):
    service, _ = _services(tmp_path, monkeypatch)
    document, _ = service.ingest(
        "acme", filename="materials.pdf", content=b"%PDF-test", mime_type="application/pdf",
        document_type="supplier_invoice", submitted_by_person_id="person.worker",
        card_asset_id="asset.worker-card",
    )
    reviewed = service.review(
        "acme", document["id"], expected_revision=1, reviewed_by_person_id="person.owner",
        fields={"supplier": "Builder Merchant", "document_date": "2026-08-09", "currency": "EUR", "net": 100, "tax": 21, "total": 121, "invoice_number": "INV-10"},
        allocation={"account_code": "310", "account_name": "Materials", "tax_code": "INPUT21"},
        destination="supplier_bill",
    )
    assert reviewed["status"] == "awaiting_approval"
    assert reviewed["authority"]["approval_route"]["recommended_approver_person_id"] == "person.owner"
    approved = service.decide(
        "acme", document["id"], decision="approve", decided_by_person_id="person.owner",
        expected_revision=2,
    )
    assert approved["status"] == "approved_for_accounting"
    assert approved["accounting"]["payload_hash"].startswith("sha256:")
    assert approved["accounting"]["exact_payload"]["destination"] == "supplier_bill"
    assert approved["accounting"]["external_write_performed"] is False
    assert approved["accounting"]["exact_payload"]["external_write_permitted"] is False


def test_missing_fields_and_unauthorised_approval_fail_closed(tmp_path, monkeypatch):
    service, _ = _services(tmp_path, monkeypatch)
    document, _ = service.ingest(
        "acme", filename="shop.png", content=b"png-two", mime_type="image/png",
        submitted_by_person_id="person.worker",
    )
    incomplete = service.review(
        "acme", document["id"], expected_revision=1,
        fields={"supplier": "Shop"}, ownership={"submitted_by_person_id": "person.worker"},
    )
    assert incomplete["status"] == "needs_information"
    complete = service.review(
        "acme", document["id"], expected_revision=2,
        fields={"supplier": "Shop", "document_date": "2026-08-09", "total": 20},
    )
    assert complete["status"] == "awaiting_approval"
    with pytest.raises(PermissionError, match="capability_not_granted"):
        service.decide(
            "acme", document["id"], decision="approve", decided_by_person_id="person.worker",
            expected_revision=3,
        )


def test_future_channels_share_one_canonical_contract(tmp_path, monkeypatch):
    service, _ = _services(tmp_path, monkeypatch)
    channels = {item["id"]: item for item in service.get("acme")["intake_channels"]}
    assert channels["desktop_upload"]["status"] == "enabled"
    assert channels["mobile_photo"]["transport"] == "same_inbox_contract"
    assert channels["agent_mailbox"]["transport"] == "email_adapter"
    assert service.get("acme")["governance"]["external_writes_enabled"] is False


def test_relative_runtime_root_matches_packaged_desktop_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", __import__("pathlib").Path(".runtime/AION_BUSINESS"))
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", __import__("pathlib").Path(".runtime/AION_BUSINESS/business_containers"))
    monkeypatch.setattr(AIONBusinessPaths, "AUDIT", __import__("pathlib").Path(".runtime/AION_BUSINESS/audit"))
    repository = BusinessContainerRepository()
    authority = OrganizationAuthorityService(repository)
    model = authority.empty("relative-business")
    model["people"] = [{"id": "person.owner", "name": "Owner", "employment_type": "owner", "status": "active", "role_ids": ["role.owner_director"]}]
    authority.save("relative-business", model)
    service = FinanceInboxService(repository)
    document, duplicate = service.ingest(
        "relative-business", filename="receipt.png", content=b"relative-image", mime_type="image/png",
        submitted_by_person_id="person.owner",
    )
    assert duplicate is False
    assert document["source"]["storage_path"].startswith("business_containers/relative-business/")
    assert service.file_path("relative-business", document["id"])[0].read_bytes() == b"relative-image"


class _FakeReader:
    def __init__(self, facts):
        self.facts = facts

    def read(self, path, *, expected_document_type):
        assert path.read_bytes()
        return {
            "facts": self.facts, "provider": "test-reader", "model": "fixture",
            "response_id": "response-1", "latency_ms": 4, "usage": {},
            "source_sent_externally": False, "provider_storage_requested": False,
        }


def _reader_facts(**updates):
    facts = {
        "document_type": "receipt", "supplier": "Build Shop", "document_date": "2026-08-09",
        "currency": "EUR", "total": 121.0, "net": 100.0, "tax": 21.0, "tip": None,
        "invoice_number": "R-10", "due_date": None, "description": "Timber and fixings",
        "payment_method": "card", "card_last_four": "1234", "merchant_tax_id": "ES123",
        "merchant_address": "1 Trade Street", "line_items": [{"description": "Timber", "quantity": 1, "unit_price": 100, "total": 100, "tax_rate": 21}],
        "category_signals": ["materials"],
        "primary_category": "materials", "primary_category_confidence": .92,
        "field_confidence": {key: .98 for key in ("supplier", "document_date", "currency", "total", "net", "tax", "invoice_number", "description", "payment_method", "line_items")},
        "uncertainties": [],
    }
    facts.update(updates)
    return facts


def test_reader_prefills_visible_facts_and_category_without_posting(tmp_path, monkeypatch):
    service, _ = _services(tmp_path, monkeypatch)
    service.receipt_reader = _FakeReader(_reader_facts())
    document, _ = service.ingest(
        "acme", filename="materials.jpg", content=b"image", mime_type="image/jpeg",
        submitted_by_person_id="person.worker",
    )
    extracted = service.extract("acme", document["id"], expected_revision=1)
    assert extracted["extraction"]["status"] == "suggestions_ready"
    assert extracted["extraction"]["fields"]["supplier"] == "Build Shop"
    assert extracted["allocation"]["category"] == "materials"
    assert extracted["extraction"]["expense_assessment"]["straight_through_candidate"] is True
    assert extracted["accounting"]["external_write_performed"] is False
    assert extracted["status"] == "needs_review"


def test_meal_receipt_requires_purpose_and_attendees_before_approval_route(tmp_path, monkeypatch):
    service, _ = _services(tmp_path, monkeypatch)
    service.receipt_reader = _FakeReader(_reader_facts(supplier="Restaurant Sol", description="Dinner", category_signals=["meal", "alcohol"]))
    document, _ = service.ingest(
        "acme", filename="dinner.jpg", content=b"dinner-image", mime_type="image/jpeg",
        submitted_by_person_id="person.worker",
    )
    extracted = service.extract("acme", document["id"])
    question_ids = {item["id"] for item in extracted["extraction"]["expense_assessment"]["questions"]}
    assert question_ids == {"business_purpose", "attendees", "alcohol_treatment"}
    incomplete = service.review(
        "acme", document["id"], fields=extracted["extraction"]["fields"],
        allocation={"category": "meal", "business_context": {"business_purpose": "Customer project meeting"}},
    )
    assert incomplete["status"] == "needs_information"
    complete = service.review(
        "acme", document["id"], fields=extracted["extraction"]["fields"],
        allocation={"category": "meal", "business_context": {"business_purpose": "Customer project meeting", "attendees": "Sam and customer", "alcohol_treatment": "Exclude wine line"}},
    )
    assert complete["status"] == "awaiting_approval"


def test_confirmed_supplier_mapping_is_reused_as_suggestion(tmp_path, monkeypatch):
    service, _ = _services(tmp_path, monkeypatch)
    first, _ = service.ingest(
        "acme", filename="first.png", content=b"first", mime_type="image/png",
        submitted_by_person_id="person.worker",
    )
    service.review(
        "acme", first["id"], fields={"supplier": "Build Shop", "document_date": "2026-08-09", "total": 10},
        allocation={"category": "materials", "account_code": "310", "account_name": "Materials"},
        reviewed_by_person_id="person.owner",
    )
    second, _ = service.ingest(
        "acme", filename="second.png", content=b"second", mime_type="image/png",
        submitted_by_person_id="person.worker",
    )
    service.receipt_reader = _FakeReader(_reader_facts(category_signals=[]))
    extracted = service.extract("acme", second["id"])
    assert extracted["allocation"]["account_code"] == "310"
    assert extracted["extraction"]["expense_assessment"]["suggestion"]["source"] == "confirmed_supplier_mapping"


def test_business_allowance_is_configured_not_assumed(tmp_path, monkeypatch):
    service, _ = _services(tmp_path, monkeypatch)
    assert service.get("acme")["expense_policy"]["meal_receipt_limit"] is None
    updated = service.update_expense_policy("acme", {"meal_receipt_limit": "35", "mileage_rate": "0.42", "receipt_reader_provider": "anthropic"}, expected_revision=0)
    assert updated["meal_receipt_limit"] == 35.0
    assert updated["mileage_rate"] == 0.42
    assert updated["receipt_reader_provider"] == "claude"
    with pytest.raises(ValueError, match="finance_receipt_reader_provider_invalid"):
        service.update_expense_policy("acme", {"receipt_reader_provider": "mystery-model"})
