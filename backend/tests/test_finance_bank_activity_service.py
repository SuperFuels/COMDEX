from __future__ import annotations

from backend.modules.aion_business.runtime.finance_bank_activity_service import FinanceBankActivityService
from backend.tests.test_finance_bookkeeping_service import configure


def test_controlled_fixture_is_explicit_exact_approved_and_ledger_ready(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    service = FinanceBankActivityService(repository, authority)
    record = service.prepare(
        "acme", source_type="controlled_test_fixture", transaction_type="spend",
        transaction_date="2026-08-09", amount=60.50, currency="EUR",
        reference="TEST-20260809-001", counterparty="FERRETERIA SOL — TESSARIS TEST",
        bank_account_id="bank-eur", source_document_id="finance-document-1",
        source_invoice_id="invoice-1", test_purpose="End-to-end receipt matching test",
        prepared_by_person_id="person.owner")
    assert record["status"] == "exact_evidence_approval_required"
    assert "not a provider-sourced" in record["truth_boundary"]
    approved = service.approve(
        "acme", record["record_id"], approved_by_person_id="person.owner",
        approved_record_hash=record["record_hash"])
    assert approved["status"] == "approved_for_matching"
    ledger = service.ledger_records("acme")
    assert ledger[0]["total"] == -60.5
    assert ledger[0]["source_ref"]["verification_status"] == "controlled_test_fixture"
    assert ledger[0]["is_reconciled"] is False
