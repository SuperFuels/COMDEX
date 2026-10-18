import base64
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.work_schedule_service import WorkScheduleService


def service(tmp_path: Path) -> WorkScheduleService:
    return WorkScheduleService(BusinessContainerRepository(tmp_path))


def test_desktop_and_mobile_share_the_same_canonical_job(tmp_path: Path) -> None:
    subject = service(tmp_path)
    created = subject.action("company", "create", {
        "title": "Roof survey", "customer": "Alex", "date": "2026-10-01", "time": "10:00",
        "duration": 90, "assignee": "James", "location": "1 High Street",
    }, actor_id="desktop")
    loaded = subject.get("company")

    assert loaded["items"][0]["id"] == created["jobs"][0]["id"]
    assert loaded["jobs"][0]["starts_at"] == "2026-10-01T10:00:00"
    assert loaded["jobs"][0]["customer"] == "Alex"


def test_customer_crm_keeps_contact_and_addresses_for_future_documents(tmp_path: Path) -> None:
    subject = service(tmp_path)
    created = subject.action("company", "create", {
        "title": "Kitchen survey", "customer_id": "customer_alex", "customer": "Alex Morgan",
        "customer_email": "alex@example.com", "customer_phone": "+44 7000 000000",
        "customer_address": "4 Billing Road", "location": "9 Service Street",
    }, actor_id="desktop")

    customer = created["customers"][0]
    assert customer["id"] == "customer_alex"
    assert customer["email"] == "alex@example.com"
    assert customer["phone"] == "+44 7000 000000"
    assert customer["billing_address"] == "4 Billing Road"
    assert customer["service_address"] == "9 Service Street"
    assert created["items"][0]["id"] in customer["work_item_ids"]


def test_secured_intake_reuses_canonical_sales_customer_during_conversion(tmp_path: Path) -> None:
    subject = service(tmp_path)
    intake_model = subject.create_intake("company", {
        "id": "intake-secured-1", "title": "Boiler service", "customer": "Alex Morgan",
        "customer_id": "contact-canonical-alex", "customer_email": "alex@example.com",
        "customer_phone": "+34 600 111 222", "customer_address": "4 Billing Road",
        "service_address": "9 Service Street", "sales_opportunity_id": "opportunity-1",
        "source_reference": "intake-endpoint:submission-1", "state": "Ready to schedule",
    }, channel="website")

    customer = intake_model["customers"][0]
    assert customer["id"] == "contact-canonical-alex"
    assert customer["sales_opportunity_id"] == "opportunity-1"
    converted = subject.action("company", "create", {
        "title": "Boiler service", "customer": customer["name"],
        "customer_id": customer["id"], "customer_email": customer["email"],
        "customer_phone": customer["phone"], "customer_address": customer["billing_address"],
        "location": customer["service_address"], "status": "scheduled",
        "source_request": {
            "id": "intake-secured-1", "source_reference": "intake-endpoint:submission-1",
            "sales_opportunity_id": "opportunity-1",
        },
    }, actor_id="desktop")

    assert converted["items"][0]["customer_id"] == "contact-canonical-alex"
    assert len(converted["customers"]) == 1
    assert converted["items"][0]["source_request"]["sales_opportunity_id"] == "opportunity-1"


def test_legacy_customer_duplicates_with_the_same_work_history_are_merged(tmp_path: Path) -> None:
    subject = service(tmp_path)
    created = subject.action("company", "create", {
        "title": "Survey", "customer_id": "customer_alex", "customer": "Alex Morgan",
        "customer_email": "alex@example.com",
    }, actor_id="desktop")
    item_id = created["items"][0]["id"]
    created["customers"].append({
        "id": "legacy_alex", "name": "Alex Morgan", "phone": "+44 7000 000000",
        "work_item_ids": [item_id],
    })

    saved = subject.save("company", created, expected_revision=created["revision"], changed_by="test")

    matching = [row for row in saved["customers"] if row["name"] == "Alex Morgan"]
    assert len(matching) == 1
    assert matching[0]["email"] == "alex@example.com"
    assert matching[0]["phone"] == "+44 7000 000000"


def test_quote_estimate_lives_on_the_same_shared_work_record(tmp_path: Path) -> None:
    subject = service(tmp_path)
    created = subject.action("company", "create", {
        "title": "Pergola quote", "customer": "Alex", "type": "quote",
        "status": "quote_required", "offering_id": "pergola-3m",
        "quote": {"status": "draft", "amount": "1500"},
        "cost_estimate": {
            "material_cost": "700", "labour_cost": "240", "external_cost": "60",
            "currency": "EUR", "note": "Initial site estimate",
        },
    }, actor_id="desktop")

    item = created["items"][0]
    assert item["type"] == "quote"
    assert item["offering_id"] == "pergola-3m"
    assert item["quote"]["amount"] == "1500.00"
    assert item["cost_estimate"] == {
        "material_cost": "700.00", "labour_cost": "240.00", "external_cost": "60.00",
        "currency": "EUR", "note": "Initial site estimate",
        "source": "shared_work_record", "updated_at": "",
    }


def test_reports_and_uploaded_evidence_are_real_files(tmp_path: Path) -> None:
    subject = service(tmp_path)
    model = subject.action("company", "create", {
        "title": "Boiler service", "date": "2026-10-01", "time": "09:00",
    }, actor_id="desktop")
    item_id = model["items"][0]["id"]
    uploaded = subject.upload(
        "company", item_id, filename="photo.jpg", content_type="image/jpeg",
        data_base64=base64.b64encode(b"real image bytes").decode(), actor_id="phone",
    )
    generated = subject.generate_document("company", item_id, "service_report", actor_id="desktop")

    upload_path, _ = subject.file_path("company", item_id, uploaded["document"]["id"])
    report_path, _ = subject.file_path("company", item_id, generated["document"]["id"])
    assert upload_path.read_bytes() == b"real image bytes"
    assert report_path.read_bytes().startswith(b"%PDF-1.4")


def test_mobile_offline_retry_is_idempotent_for_update_and_evidence(tmp_path: Path) -> None:
    subject = service(tmp_path)
    created = subject.action(
        "company", "create", {"title": "Heating commission", "assignee": "Engineer A"},
        actor_id="desktop",
    )
    item_id = created["items"][0]["id"]
    fields = {"id": item_id, "text": "Flow 61C, return 47C, pressure 1.5 bar."}

    first_update = subject.action(
        "company", "add_update", fields, actor_id="mobile-engineer",
        idempotency_key="field-update-offline-001",
    )
    replayed_update = subject.action(
        "company", "add_update", fields, actor_id="mobile-engineer",
        idempotency_key="field-update-offline-001",
    )
    image = base64.b64encode(b"real mobile camera image").decode()
    first_upload = subject.upload(
        "company", item_id, filename="commission.jpg", content_type="image/jpeg",
        data_base64=image, actor_id="mobile-engineer",
        idempotency_key="field-photo-offline-001",
    )
    replayed_upload = subject.upload(
        "company", item_id, filename="commission.jpg", content_type="image/jpeg",
        data_base64=image, actor_id="mobile-engineer",
        idempotency_key="field-photo-offline-001",
    )

    loaded = subject.get("company")
    assert first_update["idempotent_replay"] is False
    assert replayed_update["idempotent_replay"] is True
    assert first_upload["idempotent_replay"] is False
    assert replayed_upload["idempotent_replay"] is True
    assert replayed_upload["document"]["id"] == first_upload["document"]["id"]
    assert len(loaded["items"][0]["updates"]) == 1
    assert len(loaded["items"][0]["documents"]) == 1
    assert len(loaded["mobile_operation_receipts"]) == 2

    with pytest.raises(ValueError, match="reused_for_different_request"):
        subject.action(
            "company", "add_update", {"id": item_id, "text": "Different update"},
            actor_id="mobile-engineer", idempotency_key="field-update-offline-001",
        )


def test_clashes_and_recurrence_are_calculated(tmp_path: Path) -> None:
    subject = service(tmp_path)
    first = subject.action("company", "create", {
        "title": "Weekly clinic", "date": "2026-10-01", "time": "10:00", "duration": 60,
        "assignee": "Dentist A", "resource_ids": ["Room 1"],
        "recurrence": {"frequency": "weekly", "count": 3},
    }, actor_id="office")
    assert len(first["items"]) == 3
    second = subject.action("company", "create", {
        "title": "Emergency appointment", "date": "2026-10-01", "time": "10:30", "duration": 30,
        "assignee": "Dentist B", "resource_ids": ["Room 1"],
    }, actor_id="office")
    assert second["conflicts"][0]["resources"] == ["Room 1"]


def test_natural_language_prepares_a_reviewable_draft(tmp_path: Path) -> None:
    result = service(tmp_path).interpret(
        "Book a roof survey for Alex next Tuesday at 10am and assign to James"
    )
    assert result["ready"] is True
    assert result["fields"]["title"] == "roof survey"
    assert result["fields"]["customer"] == "Alex"
    assert result["fields"]["assignee"] == "James"
    assert result["fields"]["time"] == "10:00"

    update = service(tmp_path).interpret("Move Alex roof survey to next Friday at 2pm")
    assert update["intent"] == "update_work"
    assert update["query"] == "Alex roof survey"
    assert update["fields"]["time"] == "14:00"


def test_revision_conflict_prevents_silent_overwrite(tmp_path: Path) -> None:
    subject = service(tmp_path)
    subject.action("company", "create", {"title": "Visit"}, actor_id="office")
    with pytest.raises(ValueError, match="work_schedule_revision_conflict"):
        subject.save("company", {"items": []}, expected_revision=0)


def test_delivery_records_stock_time_checklist_and_materials(tmp_path: Path) -> None:
    subject = service(tmp_path)
    model = subject.action("company", "create", {"title": "Install roof"}, actor_id="office")
    item_id = model["items"][0]["id"]
    model = subject.action("company", "add_checklist", {"id": item_id, "label": "Photograph completed work"}, actor_id="engineer")
    checklist_id = model["items"][0]["checklist"][0]["id"]
    model = subject.action("company", "checklist", {"id": item_id, "checklist_id": checklist_id, "done": True}, actor_id="engineer")
    model = subject.action("company", "add_material", {"id": item_id, "name": "Roof tile", "quantity": 20, "unit": "tile", "unit_cost": "1.25"}, actor_id="engineer")
    model = subject.action("company", "add_time", {"id": item_id, "minutes": 90, "note": "Installation"}, actor_id="engineer")
    model = subject.action("company", "stock_movement", {"id": item_id, "name": "Roof tile", "quantity": 20, "movement_type": "use"}, actor_id="engineer")

    item = model["items"][0]
    assert item["checklist"][0]["done"] is True
    assert item["materials"][0]["unit_cost"] == "1.25"
    assert item["time_entries"][0]["minutes"] == 90
    assert model["stock_movements"][0]["quantity"] == -20


def test_numbered_quote_and_customer_portal_actions(tmp_path: Path) -> None:
    subject = service(tmp_path)
    model = subject.action("company", "create", {
        "title": "Boiler service", "customer": "Alex", "date": "2026-10-01", "time": "09:00",
    }, actor_id="office")
    item_id = model["items"][0]["id"]
    generated = subject.generate_document(
        "company", item_id, "quote", actor_id="office",
        line_items=[{"description": "Service labour", "quantity": 2, "unit_price": "50"}], tax_rate="20",
        document_profile={
            "business": {"name": "Example Services", "address": "1 Main Street", "accent": "#2563eb", "currency": "EUR", "bank": {"accountName": "Example Services Ltd", "bankName": "Example Bank", "sortCode": "12-34-56", "accountNumber": "12345678", "iban": "GB00 EXAMPLE"}},
            "customer": {"name": "Alex", "email": "alex@example.com"},
            "description_of_work": "Inspect the boiler, clean the burner and complete the safety checks.",
            "terms": "Valid for 30 days.", "include_terms": True, "valid_days": 30,
            "payment_method": "bank_transfer", "payment_reference": "QUOTE-NUMBER",
            "payment_schedule": [
                {"label": "Deposit", "calculated_amount": "60.00", "due_type": "acceptance"},
                {"label": "Balance", "calculated_amount": "60.00", "due_type": "completion"},
            ],
        },
    )
    assert generated["commercial"]["number"] == "Q-2026-0001"
    assert generated["commercial"]["total"] == "120.00"
    assert generated["commercial"]["document_profile"]["business"]["name"] == "Example Services"
    assert generated["commercial"]["document_profile"]["payment_reference"] == "Q-2026-0001"
    assert generated["commercial"]["payment_schedule"][0]["label"] == "Deposit"
    pdf_path, _ = subject.file_path("company", item_id, generated["document"]["id"])
    pdf_bytes = pdf_path.read_bytes()
    assert b"QUOTATION" in pdf_bytes
    assert b"Valid for 30 days" in pdf_bytes
    assert b"Inspect the boiler, clean the burner" in pdf_bytes
    assert b"Payment reference: Q-2026-0001" in pdf_bytes

    # The editable builder may retain percentage-only rows, while the numbered
    # document freezes their calculated amounts. Acceptance must invoice the
    # frozen due stage rather than falling back to the entire quote total.
    current = subject.get("company")
    current["items"][0]["quote"]["payment_schedule"] = [
        {"label": "Deposit", "amount_type": "percent", "amount_value": 50, "due_type": "acceptance"},
        {"label": "Balance", "amount_type": "percent", "amount_value": 50, "due_type": "completion"},
    ]
    subject.save("company", current, expected_revision=current["revision"], changed_by="test")

    access = subject.issue_portal_access("company", item_id, actor_id="office")
    view = subject.portal_view(access["token"])
    assert view["item"]["customer"] == "Alex"
    changed = subject.portal_action(access["token"], "approve_quote", {})
    assert changed["item"]["quote"]["status"] == "customer_approved"
    assert changed["item"]["status"] == "awaiting_payment"
    assert changed["item"]["invoice"]["number"] == "INV-2026-0001"
    assert changed["item"]["invoice"]["total"] == "60.00"
    assert changed["payment_request"]["amount"] == "60.00"
    assert changed["payment_request"]["reference"] == "Q-2026-0001"
    assert changed["payment_request"]["status"] == "preparing_delivery"
    invoice_document = next(row for row in changed["item"]["documents"] if row["kind"] == "invoice")
    invoice_path, _ = subject.file_path("company", item_id, invoice_document["id"])
    invoice_pdf = invoice_path.read_bytes()
    assert b"INVOICE" in invoice_pdf
    assert b"INVOICE FOR" in invoice_pdf
    assert b"SOURCE QUOTE" in invoice_pdf
    assert b"Q-2026-0001" in invoice_pdf
    assert b"PAYMENT DETAILS" in invoice_pdf
    assert b"TOTAL INVOICE" in invoice_pdf
    assert b"Example Services" in invoice_pdf
    assert b"BANK TRANSFER DETAILS" in invoice_pdf
    assert b"Account name: Example Services Ltd" in invoice_pdf
    assert b"Sort code / routing number: 12-34-56" in invoice_pdf
    assert b"Account number: 12345678" in invoice_pdf
    repeated = subject.portal_action(access["token"], "approve_quote", {})
    assert repeated["item"]["invoice"]["number"] == "INV-2026-0001"
    assert len([row for row in repeated["item"]["documents"] if row["kind"] == "invoice"]) == 1


def test_quote_supports_per_line_vat_without_private_cost_workings(tmp_path: Path) -> None:
    subject = service(tmp_path)
    model = subject.action("company", "create", {"title": "Custom installation", "customer": "Alex"}, actor_id="office")
    item_id = model["items"][0]["id"]
    generated = subject.generate_document(
        "company", item_id, "quote", actor_id="office", tax_rate="0",
        line_items=[
            {"description": "Labour", "type": "labour", "quantity": 1, "unit_price": "100", "tax_rate": "20"},
            {"description": "Materials", "type": "materials", "quantity": 1, "unit_price": "50", "tax_rate": "10"},
        ],
    )

    assert generated["commercial"]["subtotal"] == "150.00"
    assert generated["commercial"]["tax"] == "25.00"
    assert generated["commercial"]["total"] == "175.00"
    assert generated["commercial"]["line_items"][0]["type"] == "labour"
    assert "cost_price" not in generated["commercial"]["line_items"][0]
    assert "margin_percent" not in generated["commercial"]["line_items"][0]


def test_due_reminders_are_prepared_but_not_claimed_as_sent(tmp_path: Path) -> None:
    subject = service(tmp_path)
    subject.action("company", "create", {
        "title": "Survey", "customer": "Alex", "customer_email": "alex@example.com",
        "date": "2026-10-01", "time": "10:00",
    }, actor_id="office")
    model = subject.prepare_due_reminders("company", now=datetime(2026, 9, 30, 10, 0, tzinfo=UTC))
    assert model["reminders"][0]["status"] == "needs_approval"
    assert model["reminders"][0]["channel"] == "email"
