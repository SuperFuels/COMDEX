from __future__ import annotations

from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.finance_sales_service import FinanceSalesService
from backend.tests.test_finance_bookkeeping_service import configure


def seed_operating_model(repository) -> None:
    repository.save_dict("acme", "business_operating_model", {
        "id": "acme.business_operating_model", "workspace_id": "acme",
        "kind": "business_operating_model",
        "meta": {"workspace_id": "acme", "container_key": "business_operating_model"},
        "currency": "EUR",
        "offerings": [{
            "id": "offering.day-rate", "name": "Engineer day rate", "price": 200,
            "verification": {"status": "owner_confirmed"},
        }],
    })


def prepared_invoice(monkeypatch, tmp_path: Path):
    repository, authority = configure(monkeypatch, tmp_path)
    seed_operating_model(repository)
    service = FinanceSalesService(repository, authority)
    customer = service.create_customer(
        "acme", name="Example Customer", email="accounts@example.test",
        payment_terms_days=14, created_by_person_id="person.owner",
    )
    invoice = service.prepare_invoice(
        "acme", customer_id=customer["customer_id"], issue_date="2026-08-09",
        due_date="2026-08-23", currency="EUR", reference="Test order",
        prepared_by_person_id="person.owner", lines=[{
            "offering_id": "offering.day-rate", "quantity": 1, "unit_amount": 200,
            "tax_rate": 21, "account_code": "200", "account_name": "Sales", "tax_type": "OUTPUT",
        }],
    )
    return repository, authority, service, customer, invoice


def test_sales_invoice_is_balanced_approved_and_projected(monkeypatch, tmp_path):
    repository, _, service, customer, invoice = prepared_invoice(monkeypatch, tmp_path)
    assert invoice["subtotal"] == 200
    assert invoice["tax_total"] == 42
    assert invoice["total"] == 242
    journal = service.bookkeeping.load("acme", invoice["bookkeeping_draft_id"])
    assert journal["debit_total"] == journal["credit_total"] == 242
    assert {(row["account_code"], row["debit"], row["credit"]) for row in journal["lines"]} == {
        ("control.trade_receivables", 242, 0.0), ("200", 0.0, 200),
        ("control.output_tax", 0.0, 42),
    }
    with pytest.raises(ValueError, match="hash_mismatch"):
        service.approve_invoice("acme", invoice["invoice_id"],
                                approved_by_person_id="person.owner", approved_invoice_hash="wrong")
    approved = service.approve_invoice(
        "acme", invoice["invoice_id"], approved_by_person_id="person.owner",
        approved_invoice_hash=invoice["invoice_hash"],
    )
    assert approved["status"] == "approved_for_internal_posting"
    posted = service.post_internal("acme", invoice["invoice_id"], posted_by_person_id="person.owner")
    assert posted["status"] == "posted_internal"
    reminder = service.prepare_reminder(
        "acme", invoice["invoice_id"], tone="friendly", prepared_by_person_id="person.owner")
    assert reminder["external_message_sent"] is False
    assert reminder["status"] == "exact_message_approval_required"
    boardroom = repository.load_dict("acme", "boardroom_snapshot")
    assert boardroom["boardroom"]["runtime"]["finance_sales_invoicing"]["summary"]["outstanding"] == 242
    assert customer["provider_links"] == {}


def test_sales_invoice_validation_fails_closed(monkeypatch, tmp_path):
    _, _, service, customer, _ = prepared_invoice(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="due_date_before"):
        service.prepare_invoice(
            "acme", customer_id=customer["customer_id"], issue_date="2026-08-09",
            due_date="2026-08-08", currency="EUR", reference=None,
            prepared_by_person_id="person.owner", lines=[{"description": "Work", "quantity": 1,
                                                            "unit_amount": 1, "tax_rate": 0}],
        )


def test_verified_payment_is_exactly_once_and_conflicts_fail_closed(monkeypatch, tmp_path):
    _, _, service, _, invoice = prepared_invoice(monkeypatch, tmp_path)
    request = {
        "provider": "sandbox",
        "provider_event_id": "evt-sales-payment-1",
        "provider_payment_reference": "payment-reference-secret-1",
        "amount": 242,
        "currency": "EUR",
        "occurred_at": "2026-10-17T12:00:00+00:00",
    }
    with pytest.raises(PermissionError, match="posted_sales_invoice_required"):
        service.record_verified_payment("acme", invoice["invoice_id"], **request)
    approved = service.approve_invoice(
        "acme", invoice["invoice_id"], approved_by_person_id="person.owner",
        approved_invoice_hash=invoice["invoice_hash"],
    )
    service.post_internal("acme", approved["invoice_id"], posted_by_person_id="person.owner")
    first = service.record_verified_payment("acme", approved["invoice_id"], **request)
    assert first["idempotent_replay"] is False
    assert first["invoice"]["status"] == "paid"
    assert first["invoice"]["amount_paid"] == 242
    assert first["invoice"]["amount_due"] == 0
    replay = service.record_verified_payment("acme", approved["invoice_id"], **request)
    assert replay["idempotent_replay"] is True
    assert len(replay["invoice"]["verified_payments"]) == 1
    with pytest.raises(ValueError, match="verified_payment_event_conflict"):
        service.record_verified_payment(
            "acme", approved["invoice_id"], **{**request, "amount": 1},
        )
