"""Exact-payload export of controlled Tessaris bookkeeping entries to Xero.

The service owns the durable state machine and verification contract. Network
transport remains in the integration API so tests can prove the accounting
logic without using a live tenant. A provider response is never sufficient:
the created bill must be read back and match the frozen payload.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_bookkeeping_service import FinanceBookkeepingService
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


class XeroBookkeepingExportService:
    """Prepare, approve and verify a Xero accounts-payable bill export."""

    STATUSES = {"DRAFT", "SUBMITTED", "AUTHORISED"}

    def __init__(self, repository: BusinessContainerRepository | None = None,
                 authority: OrganizationAuthorityService | None = None,
                 bookkeeping: FinanceBookkeepingService | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = authority or OrganizationAuthorityService(self.repository)
        self.bookkeeping = bookkeeping or FinanceBookkeepingService(self.repository, self.authority)

    def prepare(self, workspace_id: str, draft_id: str, *, xero_contact_id: str,
                prepared_by_person_id: str, target_status: str = "DRAFT") -> dict[str, Any]:
        access = self.authority.access_decision(
            workspace_id, person_id=prepared_by_person_id, capability="finance.prepare"
        )
        if not access.get("allowed"):
            raise PermissionError(access.get("reason") or "finance_prepare_not_authorised")
        draft = self.bookkeeping.load(workspace_id, draft_id)
        if draft.get("status") not in {"posted_internal", "synced_to_xero"}:
            raise ValueError("posted_internal_bookkeeping_entry_required")
        existing = self.for_draft(workspace_id, draft_id)
        if existing and existing.get("status") == "verified_in_xero":
            return existing
        target_status = str(target_status or "DRAFT").upper()
        if target_status not in self.STATUSES:
            raise ValueError("unsupported_xero_bill_status")
        if not str(xero_contact_id or "").strip():
            raise ValueError("existing_xero_contact_required")

        inbox = self.repository.load_dict(workspace_id, "finance_inbox")
        document = next((item for item in inbox.get("documents") or []
                         if item.get("id") == draft.get("source_document_id")), None)
        if not document:
            raise FileNotFoundError(f"Finance document not found: {draft.get('source_document_id')}")
        instruction = (document.get("accounting") or {}).get("exact_payload") or {}
        fields = instruction.get("fields") or {}
        expense_lines = [line for line in draft.get("lines") or [] if line.get("account_type") == "expense"]
        if len(expense_lines) != 1:
            raise ValueError("single_expense_line_required_for_xero_bill_v1")
        expense = expense_lines[0]
        tax_line = next((line for line in draft.get("lines") or []
                         if line.get("account_code") == "control.input_tax"), {})
        if not expense.get("account_code") or str(expense.get("account_code")).startswith("unresolved."):
            raise ValueError("xero_expense_account_mapping_required")
        net, tax, total = _money(expense.get("debit")), _money(tax_line.get("debit")), _money(draft.get("debit_total"))
        if round(net + tax, 2) != total:
            raise ValueError("xero_bill_amounts_do_not_balance")

        reference = f"Tessaris {draft['internal_posting']['entry_id']}"
        line = {
            "Description": str(draft.get("description") or draft.get("counterparty") or "Approved business expense")[:4000],
            "Quantity": 1.0, "UnitAmount": net, "AccountCode": str(expense["account_code"]),
            "TaxAmount": tax,
        }
        if tax and tax_line.get("tax_code"):
            line["TaxType"] = str(tax_line["tax_code"])
        bill = {
            "Type": "ACCPAY", "Contact": {"ContactID": str(xero_contact_id).strip()},
            "Date": draft.get("journal_date"), "DueDate": fields.get("due_date") or draft.get("journal_date"),
            "Status": target_status, "LineAmountTypes": "Exclusive", "CurrencyCode": draft.get("currency") or "EUR",
            "Reference": reference, "LineItems": [line],
        }
        invoice_number = str(fields.get("invoice_number") or "").strip()
        if invoice_number:
            bill["InvoiceNumber"] = invoice_number[:255]
        payload = {"Invoices": [bill]}
        payload_hash = canonical_contract_hash(payload)
        source = document.get("source") or {}
        attachment = ({"filename": source.get("filename"), "mime_type": source.get("mime_type"),
                       "byte_size": source.get("byte_size"), "content_hash": source.get("content_hash")}
                      if source.get("storage_path") else None)
        approval_contract = {"endpoint": "Invoices", "payload": payload, "attachment": attachment,
                             "source_document_id": draft.get("source_document_id")}
        approval_hash = canonical_contract_hash(approval_contract)
        export_id = f"xero-export-{_safe(draft_id)}"
        record = {
            "schema_version": "aion.xero.bookkeeping_export.v1", "export_id": export_id,
            "workspace_id": workspace_id, "draft_id": draft_id,
            "source_document_id": draft.get("source_document_id"), "source_document_hash": draft.get("source_document_hash"),
            "internal_entry_id": draft["internal_posting"]["entry_id"],
            "internal_entry_hash": draft["internal_posting"]["entry_hash"],
            "provider": "xero", "operation": "create_accounts_payable_bill", "endpoint": "Invoices",
            "resource_root": "Invoices", "resource_id_field": "InvoiceID",
            "payload": payload, "payload_hash": payload_hash, "attachment": attachment,
            "approval_hash": approval_hash,
            "idempotency_key": ("aion-" + approval_hash.removeprefix("sha256:"))[:128],
            "target_status": target_status, "prepared_by_person_id": prepared_by_person_id,
            "prepared_at": _now(), "approval": None, "execution": None, "verification": None,
            "status": "exact_provider_approval_required", "external_write_performed": False,
        }
        record["export_hash"] = canonical_contract_hash(record)
        self._save(workspace_id, record)
        return record

    def approve(self, workspace_id: str, export_id: str, *, approved_by_person_id: str,
                approved_payload_hash: str) -> dict[str, Any]:
        record = self.load(workspace_id, export_id)
        if record.get("status") == "verified_in_xero":
            return record
        access = self.authority.access_decision(
            workspace_id, person_id=approved_by_person_id, capability="finance.approve_posting"
        )
        if not access.get("allowed"):
            raise PermissionError(access.get("reason") or "finance_posting_approval_not_authorised")
        if approved_payload_hash != record.get("approval_hash"):
            raise ValueError("approved_xero_payload_hash_mismatch")
        record["approval"] = {
            "approved_by_person_id": approved_by_person_id, "approved_at": _now(),
            "approved_payload_hash": approved_payload_hash, "authority_decision": access,
        }
        record["status"] = "approved_for_xero_write"
        self._rehash_save(workspace_id, record)
        return record

    def execution_request(self, workspace_id: str, export_id: str, *, executed_by_person_id: str | None = None) -> dict[str, Any]:
        record = self.load(workspace_id, export_id)
        approval = record.get("approval") or {}
        if record.get("status") == "verified_in_xero":
            return record
        if record.get("status") == "verification_failed":
            raise PermissionError("xero_verification_failed_manual_recovery_required")
        if record.get("status") not in {"approved_for_xero_write", "provider_response_received", "resource_verified_pending_attachment"}:
            raise PermissionError("exact_xero_payload_approval_required")
        if approval.get("approved_payload_hash") != record.get("approval_hash"):
            raise PermissionError("exact_xero_payload_approval_required")
        if executed_by_person_id:
            access = self.authority.access_decision(
                workspace_id, person_id=executed_by_person_id, capability="finance.prepare"
            )
            if not access.get("allowed"):
                raise PermissionError(access.get("reason") or "finance_xero_execution_not_authorised")
        return record

    def record_response(self, workspace_id: str, export_id: str, response: dict[str, Any]) -> dict[str, Any]:
        record = self.execution_request(workspace_id, export_id)
        rows = response.get(record["resource_root"]) or []
        item = rows[0] if rows and isinstance(rows[0], dict) else {}
        if item.get("HasErrors") or not item.get(record["resource_id_field"]):
            record["execution"] = {"received_at": _now(), "provider_response_hash": canonical_contract_hash(response),
                                   "validation_errors": item.get("ValidationErrors") or [], "resource_id": None}
            record["status"] = "provider_rejected"
            self._rehash_save(workspace_id, record)
            raise ValueError("xero_provider_did_not_create_bill")
        record["execution"] = {
            "received_at": _now(), "provider_response_hash": canonical_contract_hash(response),
            "resource_id": item[record["resource_id_field"]], "resource_status": item.get("Status"),
            "idempotency_key": record["idempotency_key"],
        }
        record["status"] = "provider_response_received"
        record["external_write_performed"] = True
        self._rehash_save(workspace_id, record)
        return record

    def verify_readback(self, workspace_id: str, export_id: str, response: dict[str, Any]) -> dict[str, Any]:
        record = self.load(workspace_id, export_id)
        execution = record.get("execution") or {}
        resource_id = execution.get("resource_id")
        rows = response.get(record["resource_root"]) or []
        item = next((row for row in rows if row.get(record["resource_id_field"]) == resource_id), None)
        expected = record["payload"][record["resource_root"]][0]
        errors: list[str] = []
        if not item:
            errors.append("created_resource_not_returned")
        else:
            if item.get("Type") != expected.get("Type"): errors.append("type_mismatch")
            if item.get("Reference") != expected.get("Reference"): errors.append("reference_mismatch")
            if item.get("Status") != expected.get("Status"): errors.append("status_mismatch")
            expected_total = round(sum(_money(line.get("UnitAmount")) + _money(line.get("TaxAmount"))
                                       for line in expected.get("LineItems") or []), 2)
            if abs(_money(item.get("Total")) - expected_total) > 0.02: errors.append("total_mismatch")
            contact_id = (item.get("Contact") or {}).get("ContactID")
            if contact_id != (expected.get("Contact") or {}).get("ContactID"): errors.append("contact_mismatch")
        record["verification"] = {
            "verified_at": _now(), "provider_readback_hash": canonical_contract_hash(response),
            "resource_id": resource_id, "checks": {
                "resource_identity": "created_resource_not_returned" not in errors,
                "type": "type_mismatch" not in errors, "reference": "reference_mismatch" not in errors,
                "status": "status_mismatch" not in errors, "total": "total_mismatch" not in errors,
                "contact": "contact_mismatch" not in errors,
            }, "errors": errors,
        }
        record["status"] = "verification_failed" if errors else "resource_verified_pending_attachment" if record.get("attachment") else "verified_in_xero"
        self._rehash_save(workspace_id, record)
        if errors:
            raise ValueError("xero_readback_verification_failed:" + ",".join(errors))
        if record["status"] == "verified_in_xero":
            self._project_verified(workspace_id, record)
        return record

    def verify_attachment_readback(self, workspace_id: str, export_id: str,
                                   response: dict[str, Any]) -> dict[str, Any]:
        record = self.load(workspace_id, export_id)
        if record.get("status") != "resource_verified_pending_attachment":
            raise ValueError("xero_resource_verification_required_before_attachment")
        expected = record.get("attachment") or {}
        rows = response.get("Attachments") or []
        item = next((row for row in rows if row.get("FileName") == expected.get("filename")), None)
        errors = []
        if not item or not item.get("AttachmentID"):
            errors.append("attachment_not_returned")
        if item and expected.get("mime_type") and item.get("MimeType") not in {None, expected.get("mime_type")}:
            errors.append("attachment_mime_mismatch")
        record["attachment_verification"] = {
            "verified_at": _now(), "provider_readback_hash": canonical_contract_hash(response),
            "attachment_id": (item or {}).get("AttachmentID"), "filename": expected.get("filename"),
            "source_content_hash": expected.get("content_hash"), "errors": errors,
        }
        record["status"] = "verification_failed" if errors else "verified_in_xero"
        self._rehash_save(workspace_id, record)
        if errors:
            raise ValueError("xero_attachment_verification_failed:" + ",".join(errors))
        self._project_verified(workspace_id, record)
        return record

    def load(self, workspace_id: str, export_id: str) -> dict[str, Any]:
        path = self._dir(workspace_id) / f"{_safe(export_id)}.json"
        if not path.exists():
            raise FileNotFoundError(f"Xero bookkeeping export not found: {export_id}")
        value = json.loads(path.read_text(encoding="utf-8"))
        expected = value.get("export_hash"); payload = dict(value); payload.pop("export_hash", None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError("xero_bookkeeping_export_hash_mismatch")
        if value.get("workspace_id") != workspace_id:
            raise PermissionError("xero_bookkeeping_export_workspace_isolation_violation")
        return value

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load(workspace_id, path.stem) for path in sorted(
            self._dir(workspace_id).glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True
        )]

    def for_draft(self, workspace_id: str, draft_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list(workspace_id) if item.get("draft_id") == draft_id), None)

    def _dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/xero_bookkeeping_exports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _save(self, workspace_id: str, value: dict[str, Any]) -> None:
        (self._dir(workspace_id) / f"{_safe(value['export_id'])}.json").write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def _rehash_save(self, workspace_id: str, value: dict[str, Any]) -> None:
        value.pop("export_hash", None); value["export_hash"] = canonical_contract_hash(value)
        self._save(workspace_id, value)

    def _project_verified(self, workspace_id: str, record: dict[str, Any]) -> None:
        draft = self.bookkeeping.load(workspace_id, record["draft_id"])
        draft.setdefault("provider_exports", {})["xero"] = {
            "export_id": record["export_id"], "export_hash": record["export_hash"],
            "resource_id": record["verification"]["resource_id"], "verified_at": record["verification"]["verified_at"],
            "status": "verified_in_xero", "payload_hash": record["payload_hash"],
        }
        draft["status"] = "synced_to_xero"
        draft.pop("draft_hash", None); draft["draft_hash"] = canonical_contract_hash(draft)
        self.bookkeeping._save_draft(workspace_id, draft)
        summary = {
            "export_id": record["export_id"], "resource_id": record["verification"]["resource_id"],
            "verified_at": record["verification"]["verified_at"], "payload_hash": record["payload_hash"],
            "source_document_id": record["source_document_id"], "status": "verified_in_xero",
        }
        inbox = self.repository.load_optional_dict(workspace_id, "finance_inbox")
        if inbox:
            document = next((item for item in inbox.get("documents") or []
                             if item.get("id") == record.get("source_document_id")), None)
            if document:
                document.setdefault("accounting", {}).update({
                    "status": "verified_in_xero", "provider": "xero",
                    "external_write_performed": True,
                    "provider_export": summary,
                })
                document["status"] = "verified_in_xero"
                document["updated_at"] = record["verification"]["verified_at"]
                history = document.setdefault("history", [])
                if not any(item.get("event") == "document_verified_in_xero"
                           and item.get("export_id") == record.get("export_id") for item in history):
                    history.append({
                        "event": "document_verified_in_xero",
                        "at": record["verification"]["verified_at"],
                        "export_id": record["export_id"],
                        "resource_id": record["verification"]["resource_id"],
                    })
                inbox["revision"] = int(inbox.get("revision") or 0) + 1
                self.repository.save_dict(workspace_id, "finance_inbox", inbox)
        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            intelligence.setdefault("departments", {}).setdefault("finance", {})["latest_verified_xero_export"] = summary
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1
            self.repository.save_dict(workspace_id, "department_intelligence", intelligence)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom:
            runtime = boardroom.setdefault("boardroom", {}).setdefault("runtime", {})
            runtime["latest_verified_xero_export"] = summary
            runtime["finance_internal_ledger"] = self.bookkeeping.ledger_summary(workspace_id)
            self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)
        tree = WorkflowFileCabinetRepository.load(workspace_id)
        folders = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        finance = next((item for item in folders if item.get("id") == "folder_finance"), None)
        if finance is None:
            finance = {"id": "folder_finance", "name": "Finance", "type": "department", "children": []}; folders.append(finance)
        children = finance.setdefault("children", [])
        folder = next((item for item in children if item.get("id") == "folder_finance_xero_exports"), None)
        if folder is None:
            folder = {"id": "folder_finance_xero_exports", "name": "Verified Xero Exports", "type": "folder", "children": []}; children.append(folder)
        if not any(item.get("id") == f"xero_export_{record['export_id']}" for item in folder.setdefault("children", [])):
            path = self._dir(workspace_id) / f"{_safe(record['export_id'])}.json"
            folder["children"].append({"id": f"xero_export_{record['export_id']}", "name": record["export_id"],
                "type": "business_container_artifact", "document_type": "verified_xero_bookkeeping_export",
                "status": "verified_in_xero", "target": {"storage_path": str(path), "export_hash": record["export_hash"]}})
        tree["folders"] = folders
        tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}
        WorkflowFileCabinetRepository.save(workspace_id, tree)
