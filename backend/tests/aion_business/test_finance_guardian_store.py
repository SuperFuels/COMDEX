from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.finance_sales_service import FinanceSalesService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.tests.test_finance_bookkeeping_service import configure
from backend.tests.test_finance_sales_service import seed_operating_model


def test_finance_sales_and_bookkeeping_restart_from_encrypted_vault(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    seed_operating_model(repository)
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"f" * 32)
    domains = VaultDomainStore(guardian)
    subject = FinanceSalesService(repository, authority, domain_store=domains)
    customer = subject.create_customer(
        "acme", name="Private Finance Customer", email="finance-private@example.test",
        payment_terms_days=14, created_by_person_id="person.owner",
    )
    invoice = subject.prepare_invoice(
        "acme", customer_id=customer["customer_id"], issue_date="2026-10-17",
        due_date="2026-10-31", currency="EUR", reference="Private order",
        lines=[{"description": "Private service", "quantity": 1, "unit_amount": 250,
                "tax_rate": 20, "account_code": "200", "account_name": "Sales"}],
        prepared_by_person_id="person.owner",
    )
    approved = subject.approve_invoice(
        "acme", invoice["invoice_id"], approved_by_person_id="person.owner",
        approved_invoice_hash=invoice["invoice_hash"],
    )
    subject.post_internal("acme", approved["invoice_id"], posted_by_person_id="person.owner")
    payment_request = {
        "provider": "qualification_sandbox",
        "provider_event_id": "evt-finance-guardian-1",
        "provider_payment_reference": "provider-payment-private-1",
        "amount": 300,
        "currency": "EUR",
        "occurred_at": "2026-10-17T12:00:00+00:00",
    }
    payment = subject.record_verified_payment(
        "acme", approved["invoice_id"], **payment_request,
    )
    assert payment["invoice"]["status"] == "paid"
    assert payment["invoice"]["amount_due"] == 0
    assert payment["idempotent_replay"] is False
    replay = subject.record_verified_payment(
        "acme", approved["invoice_id"], **payment_request,
    )
    assert replay["idempotent_replay"] is True
    assert len(replay["invoice"]["verified_payments"]) == 1
    with pytest.raises(ValueError, match="verified_payment_event_conflict"):
        subject.record_verified_payment(
            "acme", approved["invoice_id"], **{**payment_request, "amount": 1},
        )

    restarted = FinanceSalesService(repository, authority, domain_store=domains)
    assert restarted.load_customer("acme", customer["customer_id"])["name"] == "Private Finance Customer"
    restored_invoice = restarted.load_invoice("acme", invoice["invoice_id"])
    assert restored_invoice["status"] == "paid"
    assert restored_invoice["amount_paid"] == 300
    assert len(restored_invoice["verified_payments"]) == 1
    assert restarted.bookkeeping.ledger_summary("acme")["entry_count"] == 1
    assert domains.list("finance.bookkeeping_journal", workspace_id="acme")
    reconciliation = domains.list("finance.reconciliation_records", workspace_id="acme")
    assert len(reconciliation) == 1
    assert reconciliation[0]["payload"]["receipt_hash"] == payment["payment"]["receipt_hash"]
    assert not (repository.base_dir / "acme" / "finance" / "sales").exists()
    assert not (repository.base_dir / "acme" / "finance" / "bookkeeping").exists()
    assert b"Private Finance Customer" not in guardian.database.read_bytes()
    assert b"Private order" not in guardian.database.read_bytes()
    assert b"provider-payment-private-1" not in guardian.database.read_bytes()
