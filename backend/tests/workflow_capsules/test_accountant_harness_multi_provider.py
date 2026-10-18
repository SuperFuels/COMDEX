from __future__ import annotations

from pathlib import Path

from backend.modules.aion_business.providers.freeagent_accounting_adapter import FreeAgentAccountingAdapter
from backend.modules.aion_business.providers.freshbooks_accounting_adapter import FreshBooksAccountingAdapter
from backend.modules.aion_business.providers.quickbooks_online_accounting_adapter import QuickBooksOnlineAccountingAdapter
from backend.modules.aion_business.providers.sage_accounting_adapter import SageAccountingAdapter
from backend.modules.aion_business.providers.zoho_books_accounting_adapter import ZohoBooksAccountingAdapter
from backend.modules.aion_business.runtime.accountant_harness_service import AccountantHarnessService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _runtime(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "AION_BUSINESS"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", root / "business_containers")
    monkeypatch.setattr(AIONBusinessPaths, "WORKSPACES", root / "workspaces")


def test_quickbooks_normalises_invoices_payments_and_purchases() -> None:
    records = QuickBooksOnlineAccountingAdapter().normalize_snapshot({
        "accounts": [{"Id": "1", "Name": "Bank", "AcctNum": "100", "AccountType": "Bank"}],
        "invoices": [{"Id": "10", "DocNumber": "INV-10", "TxnDate": "2026-09-01", "DueDate": "2026-09-30",
                      "TotalAmt": 120, "Balance": 0, "CustomerRef": {"value": "c1", "name": "Client"}}],
        "bills": [{"Id": "20", "DocNumber": "BILL-20", "TotalAmt": 60, "Balance": 60,
                   "VendorRef": {"value": "v1", "name": "Supplier"}}],
        "payments": [{"Id": "30", "TxnDate": "2026-09-03", "TotalAmt": 120,
                      "Line": [{"LinkedTxn": [{"TxnId": "10", "TxnType": "Invoice"}]}]}],
        "purchases": [{"Id": "40", "TxnDate": "2026-09-04", "TotalAmt": 12, "PaymentType": "Cash"}],
        "journal_entries": [],
    }, sync_id="qbo-sync", company_id="realm-1")
    assert len(records["invoices"]) == 2
    assert records["invoices"][0]["invoice_type"] == "sales_invoice"
    assert records["invoices"][1]["invoice_type"] == "supplier_bill"
    assert records["payments"][0]["invoice_id"] == "10"
    assert records["bank_transactions"][0]["total"] == -12
    assert records["accounts"][0]["source_ref"]["provider"] == "quickbooks_online"


def test_sage_normalises_accounting_evidence() -> None:
    records = SageAccountingAdapter().normalize_snapshot({
        "ledger_accounts": [{"id": "a1", "nominal_code": "4000", "displayed_as": "Sales"}],
        "sales_invoices": [{"id": "i1", "displayed_as": "SI-1", "total_amount": 80,
                            "outstanding_amount": 20, "contact": {"id": "c1", "displayed_as": "Client"}}],
        "purchase_invoices": [],
        "contact_payments": [{"id": "p1", "total_amount": 60, "transaction": {"id": "i1", "displayed_as": "SI-1"}}],
        "bank_account_transactions": [{"id": "b1", "total_amount": 60, "reconciled": True}],
        "ledger_entries": [],
    }, sync_id="sage-sync", company_id="business-1")
    assert records["invoices"][0]["amount_paid"] == 60
    assert records["payments"][0]["invoice_id"] == "i1"
    assert records["bank_transactions"][0]["is_reconciled"] is True
    assert records["accounts"][0]["source_ref"]["provider"] == "sage_accounting"


def test_freeagent_normalises_invoices_bank_activity_and_journals() -> None:
    records = FreeAgentAccountingAdapter().normalize_snapshot({
        "categories": [{"url": "https://api.freeagent.com/v2/categories/001", "nominal_code": "001", "description": "Sales"}],
        "contacts": [{"url": "https://api.freeagent.com/v2/contacts/7", "organisation_name": "Client Ltd"}],
        "invoices": [{"url": "https://api.freeagent.com/v2/invoices/10", "reference": "INV-10", "contact": "https://api.freeagent.com/v2/contacts/7", "total_value": "120", "due_value": "20", "status": "Overdue"}],
        "bills": [], "bank_accounts": [],
        "bank_transactions": [{"url": "https://api.freeagent.com/v2/bank_transactions/9", "amount": "100", "unexplained_amount": "0", "description": "Client Ltd"}],
        "journal_sets": [{"url": "https://api.freeagent.com/v2/journal_sets/2", "description": "Correction", "journal_entries": [{"debit_value": "10"}, {"debit_value": "-10"}]}],
    }, sync_id="fa-sync", company_id="company")
    assert records["invoices"][0]["contact"]["display_name"] == "Client Ltd"
    assert records["invoices"][0]["amount_paid"] == 100
    assert records["bank_transactions"][0]["is_reconciled"] is True
    assert records["manual_journals"][0]["net_amount"] == 0


def test_freshbooks_normalises_service_business_records() -> None:
    records = FreshBooksAccountingAdapter().normalize_snapshot({
        "chart_of_accounts": [{"account_uuid": "a1", "account_number": "1000", "account_name": "Cash", "account_type": "asset", "state": "active"}],
        "invoices": [{"invoiceid": 10, "invoice_number": "FB-10", "amount": {"amount": "85", "code": "GBP"}, "outstanding": {"amount": "25"}, "customerid": 7}],
        "bills": [{"id": 13, "bill_number": "B-13", "total_amount": {"amount": "45", "code": "GBP"}, "outstanding": {"amount": "5"}, "status": "partial", "vendorid": 9,
                   "bill_payments": [{"id": 14, "amount": {"amount": "40"}, "date": "2026-09-19"}]}],
        "payments": [{"id": 11, "invoiceid": 10, "amount": {"amount": "60", "code": "GBP"}, "date": "2026-09-20"}],
        "expenses": [{"expenseid": 12, "amount": {"amount": "15", "code": "GBP"}, "vendor": "Supplier", "date": "2026-09-21"}],
    }, sync_id="fb-sync", company_id="account|business")
    assert records["accounts"][0]["name"] == "Cash"
    assert records["invoices"][0]["amount_due"] == 25
    assert records["invoices"][1]["invoice_type"] == "supplier_bill"
    assert records["invoices"][1]["amount_paid"] == 40
    assert records["payments"][0]["invoice_id"] == "13"
    assert records["payments"][1]["invoice_id"] == "10"
    assert records["bank_transactions"][0]["total"] == -15


def test_zoho_books_normalises_invoices_bills_payments_and_bank_activity() -> None:
    records = ZohoBooksAccountingAdapter().normalize_snapshot({
        "chartofaccounts": [{"account_id": "a1", "account_code": "100", "account_name": "Bank", "account_type": "bank"}],
        "invoices": [{"invoice_id": "i1", "invoice_number": "Z-1", "total": 90, "balance": 30, "customer_id": "c1", "status": "overdue"}],
        "bills": [{"bill_id": "b1", "bill_number": "B-1", "total": 40, "balance": 40, "vendor_id": "v1"}],
        "customerpayments": [{"payment_id": "p1", "amount": 60, "invoices": [{"invoice_id": "i1", "invoice_number": "Z-1"}]}],
        "vendorpayments": [],
        "banktransactions": [{"transaction_id": "t1", "transaction_type": "withdrawal", "amount": 8, "reconcile_status": "reconciled"}],
        "journals": [],
    }, sync_id="zoho-sync", company_id="org-1")
    assert len(records["invoices"]) == 2
    assert records["payments"][0]["invoice_id"] == "i1"
    assert records["bank_transactions"][0]["total"] == -8
    assert records["bank_transactions"][0]["is_reconciled"] is True


def test_accountant_harness_creates_shared_ledger_and_reconciliation(monkeypatch, tmp_path: Path) -> None:
    _runtime(monkeypatch, tmp_path)
    service = AccountantHarnessService()
    result = service.ingest("home-fixed", "quickbooks_online", {
        "accounts": [],
        "invoices": [{"Id": "10", "DocNumber": "INV-10", "TxnDate": "2026-09-01", "DueDate": "2026-09-30",
                      "TotalAmt": 120, "Balance": 0, "CustomerRef": {"value": "c1", "name": "Client"}}],
        "bills": [],
        "payments": [{"Id": "30", "TxnDate": "2026-09-03", "TotalAmt": 120,
                      "Line": [{"LinkedTxn": [{"TxnId": "10", "TxnType": "Invoice"}]}]}],
        "purchases": [], "journal_entries": [],
    }, company_id="realm-1")
    assert result["ledger"]["provider"] == "quickbooks_online"
    assert result["ledger"]["external_write_performed"] is False
    reconciliation = service.reconcile("home-fixed")
    assert reconciliation["match_count"] == 1
    assert reconciliation["matches"][0]["confidence"] == "high"
    assert reconciliation["external_write_performed"] is False


def test_catalog_does_not_claim_unverified_live_accounting() -> None:
    catalog = AccountantHarnessService().catalog()
    providers = {row["provider_id"]: row for row in catalog["providers"]}
    assert providers["quickbooks_online"]["implementation"] == "read_adapter_and_canonical_harness_ready"
    assert providers["sage_accounting"]["implementation"] == "read_adapter_and_canonical_harness_ready"
    assert providers["quickbooks_online"]["bank_reconciliation_api"] is False
    assert providers["freeagent"]["implementation"] == "read_adapter_and_canonical_harness_ready"
    assert providers["freshbooks"]["implementation"] == "read_adapter_and_canonical_harness_ready"
    assert providers["zoho_books"]["implementation"] == "read_adapter_and_canonical_harness_ready"
