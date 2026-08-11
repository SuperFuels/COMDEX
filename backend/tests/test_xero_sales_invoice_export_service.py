from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.xero_sales_invoice_export_service import XeroSalesInvoiceExportService
from backend.tests.test_finance_sales_service import prepared_invoice


def posted_invoice(monkeypatch, tmp_path):
    repository, authority, sales, _, invoice = prepared_invoice(monkeypatch, tmp_path)
    invoice = sales.approve_invoice(
        "acme", invoice["invoice_id"], approved_by_person_id="person.owner",
        approved_invoice_hash=invoice["invoice_hash"])
    invoice = sales.post_internal("acme", invoice["invoice_id"], posted_by_person_id="person.owner")
    return repository, authority, sales, invoice


def test_exact_approved_xero_sales_invoice_round_trip(monkeypatch, tmp_path):
    repository, authority, sales, invoice = posted_invoice(monkeypatch, tmp_path)
    service = XeroSalesInvoiceExportService(repository, authority, sales.bookkeeping, sales)
    record = service.prepare(
        "acme", invoice["invoice_id"], xero_contact_id="contact-123",
        prepared_by_person_id="person.owner", target_status="DRAFT")
    payload = record["payload"]["Invoices"][0]
    assert payload["Type"] == "ACCREC"
    assert payload["Contact"]["ContactID"] == "contact-123"
    assert payload["LineItems"][0]["AccountCode"] == "200"
    with pytest.raises(ValueError, match="hash_mismatch"):
        service.approve("acme", record["export_id"], approved_by_person_id="person.owner",
                        approved_payload_hash="wrong")
    record = service.approve(
        "acme", record["export_id"], approved_by_person_id="person.owner",
        approved_payload_hash=record["approval_hash"])
    service.execution_request("acme", record["export_id"], executed_by_person_id="person.owner")
    record = service.record_response("acme", record["export_id"], {
        "Invoices": [{"InvoiceID": "xero-invoice-1", "Status": "DRAFT", "HasErrors": False}],
    })
    record = service.verify("acme", record["export_id"], {"Invoices": [{
        "InvoiceID": "xero-invoice-1", "Type": "ACCREC", "InvoiceNumber": invoice["invoice_number"],
        "Status": "DRAFT", "Contact": {"ContactID": "contact-123"}, "Total": 242,
    }]})
    assert record["status"] == "verified_in_xero"
    assert sales.load_invoice("acme", invoice["invoice_id"])["status"] == "verified_in_xero"
    assert sales.bookkeeping.load("acme", invoice["bookkeeping_draft_id"])["status"] == "synced_to_xero"


def test_xero_sales_invoice_readback_mismatch_fails(monkeypatch, tmp_path):
    repository, authority, sales, invoice = posted_invoice(monkeypatch, tmp_path)
    service = XeroSalesInvoiceExportService(repository, authority, sales.bookkeeping, sales)
    record = service.prepare("acme", invoice["invoice_id"], xero_contact_id="contact-123",
                             prepared_by_person_id="person.owner")
    record = service.approve("acme", record["export_id"], approved_by_person_id="person.owner",
                             approved_payload_hash=record["approval_hash"])
    service.record_response("acme", record["export_id"], {
        "Invoices": [{"InvoiceID": "xero-invoice-2", "Status": "DRAFT", "HasErrors": False}]})
    with pytest.raises(ValueError, match="total_mismatch"):
        service.verify("acme", record["export_id"], {"Invoices": [{
            "InvoiceID": "xero-invoice-2", "Type": "ACCREC", "InvoiceNumber": invoice["invoice_number"],
            "Status": "DRAFT", "Contact": {"ContactID": "contact-123"}, "Total": 1,
        }]})

