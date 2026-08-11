from __future__ import annotations

from pathlib import Path
from hashlib import sha256

import pytest

from backend.modules.aion_business.runtime.finance_bookkeeping_service import FinanceBookkeepingService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.xero_bookkeeping_export_service import XeroBookkeepingExportService
from backend.tests.test_finance_bookkeeping_service import configure, seed_document


def posted_bookkeeping(monkeypatch, tmp_path: Path):
    repository, authority = configure(monkeypatch, tmp_path)
    seed_document(repository)
    bookkeeping = FinanceBookkeepingService(repository, authority)
    draft = bookkeeping.prepare_document("acme", "finance-document-1", prepared_by_person_id="person.owner")
    approved = bookkeeping.approve(
        "acme", draft["draft_id"], approved_by_person_id="person.owner", approved_draft_hash=draft["draft_hash"]
    )
    posted = bookkeeping.post_internal("acme", approved["draft_id"], posted_by_person_id="person.owner")
    return repository, authority, bookkeeping, posted


def xero_created_response(record):
    bill = record["payload"]["Invoices"][0]
    total = sum(float(line["UnitAmount"]) + float(line.get("TaxAmount") or 0) for line in bill["LineItems"])
    return {"Invoices": [{**bill, "InvoiceID": "xero-invoice-1", "Total": total, "HasErrors": False}]}


def test_exact_approved_bill_is_idempotent_and_requires_readback(monkeypatch, tmp_path):
    repository, authority, bookkeeping, draft = posted_bookkeeping(monkeypatch, tmp_path)
    service = XeroBookkeepingExportService(repository, authority, bookkeeping)
    record = service.prepare(
        "acme", draft["draft_id"], xero_contact_id="xero-contact-1",
        prepared_by_person_id="person.owner", target_status="DRAFT",
    )
    bill = record["payload"]["Invoices"][0]
    assert bill["Type"] == "ACCPAY"
    assert bill["Contact"] == {"ContactID": "xero-contact-1"}
    assert bill["LineItems"][0]["AccountCode"] == "500"
    assert bill["LineItems"][0]["TaxAmount"] == 10.5
    assert bill["DueDate"] == "2026-08-16"
    assert record["external_write_performed"] is False
    assert len(record["idempotency_key"]) <= 128

    with pytest.raises(ValueError, match="payload_hash_mismatch"):
        service.approve("acme", record["export_id"], approved_by_person_id="person.owner",
                        approved_payload_hash="sha256:wrong")
    record = service.approve(
        "acme", record["export_id"], approved_by_person_id="person.owner",
        approved_payload_hash=record["approval_hash"],
    )
    service.execution_request("acme", record["export_id"], executed_by_person_id="person.owner")
    response = xero_created_response(record)
    received = service.record_response("acme", record["export_id"], response)
    assert received["status"] == "provider_response_received"
    assert received["external_write_performed"] is True
    verified = service.verify_readback("acme", record["export_id"], response)
    assert verified["status"] == "verified_in_xero"
    assert all(verified["verification"]["checks"].values())
    assert service.prepare("acme", draft["draft_id"], xero_contact_id="different",
                           prepared_by_person_id="person.owner") == verified
    synced = bookkeeping.load("acme", draft["draft_id"])
    assert synced["status"] == "synced_to_xero"
    assert synced["provider_exports"]["xero"]["resource_id"] == "xero-invoice-1"
    boardroom = repository.load_dict("acme", "boardroom_snapshot")
    assert boardroom["boardroom"]["runtime"]["latest_verified_xero_export"]["resource_id"] == "xero-invoice-1"
    inbox = repository.load_dict("acme", "finance_inbox")
    document = inbox["documents"][0]
    assert document["status"] == "verified_in_xero"
    assert document["accounting"]["provider"] == "xero"
    assert document["accounting"]["external_write_performed"] is True
    assert document["accounting"]["provider_export"]["resource_id"] == "xero-invoice-1"


def test_xero_export_fails_closed_for_missing_contact_and_bad_readback(monkeypatch, tmp_path):
    repository, authority, bookkeeping, draft = posted_bookkeeping(monkeypatch, tmp_path)
    service = XeroBookkeepingExportService(repository, authority, bookkeeping)
    with pytest.raises(ValueError, match="existing_xero_contact_required"):
        service.prepare("acme", draft["draft_id"], xero_contact_id="", prepared_by_person_id="person.owner")
    record = service.prepare("acme", draft["draft_id"], xero_contact_id="contact-1",
                             prepared_by_person_id="person.owner")
    record = service.approve("acme", record["export_id"], approved_by_person_id="person.owner",
                             approved_payload_hash=record["approval_hash"])
    response = xero_created_response(record)
    service.record_response("acme", record["export_id"], response)
    response["Invoices"][0]["Total"] = 999
    with pytest.raises(ValueError, match="total_mismatch"):
        service.verify_readback("acme", record["export_id"], response)
    failed = service.load("acme", record["export_id"])
    assert failed["status"] == "verification_failed"
    assert failed["verification"]["errors"] == ["total_mismatch"]


def test_receipt_attachment_is_in_exact_approval_and_must_be_read_back(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    seed_document(repository)
    content = b"protected-receipt-image"
    path = AIONBusinessPaths.business_container_dir("acme") / "finance/inbox/documents/finance-document-1/original.png"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
    inbox = repository.load_dict("acme", "finance_inbox")
    inbox["documents"][0]["source"] = {
        "filename": "receipt.png", "mime_type": "image/png", "byte_size": len(content),
        "content_hash": "sha256:" + sha256(content).hexdigest(),
        "storage_path": str(path.relative_to(AIONBusinessPaths.ROOT)),
    }
    repository.save_dict("acme", "finance_inbox", inbox)
    bookkeeping = FinanceBookkeepingService(repository, authority)
    draft = bookkeeping.prepare_document("acme", "finance-document-1", prepared_by_person_id="person.owner")
    draft = bookkeeping.approve("acme", draft["draft_id"], approved_by_person_id="person.owner",
                                approved_draft_hash=draft["draft_hash"])
    draft = bookkeeping.post_internal("acme", draft["draft_id"], posted_by_person_id="person.owner")
    service = XeroBookkeepingExportService(repository, authority, bookkeeping)
    record = service.prepare("acme", draft["draft_id"], xero_contact_id="contact-1",
                             prepared_by_person_id="person.owner")
    assert record["attachment"]["content_hash"] == "sha256:" + sha256(content).hexdigest()
    assert record["approval_hash"] != record["payload_hash"]
    record = service.approve("acme", record["export_id"], approved_by_person_id="person.owner",
                             approved_payload_hash=record["approval_hash"])
    response = xero_created_response(record)
    service.record_response("acme", record["export_id"], response)
    record = service.verify_readback("acme", record["export_id"], response)
    assert record["status"] == "resource_verified_pending_attachment"
    verified = service.verify_attachment_readback("acme", record["export_id"], {
        "Attachments": [{"AttachmentID": "attachment-1", "FileName": "receipt.png", "MimeType": "image/png"}]
    })
    assert verified["status"] == "verified_in_xero"
    assert verified["attachment_verification"]["source_content_hash"] == record["attachment"]["content_hash"]
