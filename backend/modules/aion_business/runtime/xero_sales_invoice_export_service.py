"""Exact-approved Xero accounts-receivable invoice export."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_bookkeeping_service import FinanceBookkeepingService
from backend.modules.aion_business.runtime.finance_sales_service import FinanceSalesService
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


class XeroSalesInvoiceExportService:
    STATUSES = {"DRAFT", "SUBMITTED", "AUTHORISED"}

    def __init__(self, repository: BusinessContainerRepository | None = None,
                 authority: OrganizationAuthorityService | None = None,
                 bookkeeping: FinanceBookkeepingService | None = None,
                 sales: FinanceSalesService | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = authority or OrganizationAuthorityService(self.repository)
        self.bookkeeping = bookkeeping or FinanceBookkeepingService(self.repository, self.authority)
        self.sales = sales or FinanceSalesService(self.repository, self.authority, self.bookkeeping)

    def prepare(self, workspace_id: str, invoice_id: str, *, xero_contact_id: str,
                prepared_by_person_id: str, target_status: str = "DRAFT") -> dict[str, Any]:
        access = self.authority.access_decision(
            workspace_id, person_id=prepared_by_person_id, capability="finance.prepare")
        if not access.get("allowed"):
            raise PermissionError(access.get("reason") or "finance_prepare_not_authorised")
        invoice = self.sales.load_invoice(workspace_id, invoice_id)
        if invoice.get("status") not in {"posted_internal", "verified_in_xero"}:
            raise ValueError("posted_internal_sales_invoice_required")
        existing = self.for_invoice(workspace_id, invoice_id)
        if existing and existing.get("status") == "verified_in_xero":
            return existing
        target_status = str(target_status or "DRAFT").upper()
        if target_status not in self.STATUSES:
            raise ValueError("unsupported_xero_sales_invoice_status")
        if not str(xero_contact_id or "").strip():
            raise ValueError("existing_xero_customer_contact_required")
        payload_lines = []
        for line in invoice.get("lines") or []:
            item = {
                "Description": line["description"], "Quantity": line["quantity"],
                "UnitAmount": line["unit_amount"], "AccountCode": line["account_code"],
                "TaxAmount": line["tax_amount"],
            }
            if line.get("tax_type"):
                item["TaxType"] = line["tax_type"]
            payload_lines.append(item)
        bill = {
            "Type": "ACCREC", "Contact": {"ContactID": str(xero_contact_id).strip()},
            "Date": invoice["issue_date"], "DueDate": invoice["due_date"],
            "Status": target_status, "LineAmountTypes": "Exclusive",
            "CurrencyCode": invoice["currency"], "InvoiceNumber": invoice["invoice_number"],
            "Reference": invoice.get("reference") or f"Tessaris {invoice_id}",
            "LineItems": payload_lines,
        }
        payload = {"Invoices": [bill]}
        approval_contract = {"endpoint": "Invoices", "payload": payload,
                             "source_invoice_id": invoice_id, "source_invoice_hash": invoice["invoice_hash"]}
        approval_hash = canonical_contract_hash(approval_contract)
        export_id = f"xero-sales-export-{_safe(invoice_id)}"
        record = {
            "schema_version": "aion.xero.sales_invoice_export.v1", "export_id": export_id,
            "workspace_id": workspace_id, "invoice_id": invoice_id,
            "source_invoice_hash": invoice["invoice_hash"], "provider": "xero",
            "operation": "create_accounts_receivable_invoice", "endpoint": "Invoices",
            "resource_root": "Invoices", "resource_id_field": "InvoiceID",
            "payload": payload, "payload_hash": canonical_contract_hash(payload),
            "approval_hash": approval_hash,
            "idempotency_key": ("aion-" + approval_hash.removeprefix("sha256:"))[:128],
            "target_status": target_status, "prepared_at": _now(),
            "prepared_by_person_id": prepared_by_person_id, "approval": None,
            "execution": None, "verification": None,
            "status": "exact_provider_approval_required", "external_write_performed": False,
        }
        self._rehash_save(workspace_id, record)
        return record

    def approve(self, workspace_id: str, export_id: str, *, approved_by_person_id: str,
                approved_payload_hash: str) -> dict[str, Any]:
        record = self.load(workspace_id, export_id)
        if record.get("status") == "verified_in_xero":
            return record
        access = self.authority.access_decision(
            workspace_id, person_id=approved_by_person_id, capability="finance.approve_posting")
        if not access.get("allowed"):
            raise PermissionError(access.get("reason") or "finance_posting_approval_not_authorised")
        if approved_payload_hash != record.get("approval_hash"):
            raise ValueError("approved_xero_sales_invoice_hash_mismatch")
        record["approval"] = {"approved_by_person_id": approved_by_person_id, "approved_at": _now(),
                              "approved_payload_hash": approved_payload_hash, "authority_decision": access}
        record["status"] = "approved_for_xero_write"
        self._rehash_save(workspace_id, record); return record

    def execution_request(self, workspace_id: str, export_id: str, *, executed_by_person_id: str) -> dict[str, Any]:
        record = self.load(workspace_id, export_id)
        if record.get("status") == "verified_in_xero":
            return record
        if record.get("status") == "verification_failed":
            raise PermissionError("xero_sales_invoice_verification_failed_manual_recovery_required")
        if record.get("status") not in {"approved_for_xero_write", "provider_response_received"}:
            raise PermissionError("exact_xero_sales_invoice_approval_required")
        if (record.get("approval") or {}).get("approved_payload_hash") != record.get("approval_hash"):
            raise PermissionError("exact_xero_sales_invoice_approval_required")
        access = self.authority.access_decision(
            workspace_id, person_id=executed_by_person_id, capability="finance.prepare")
        if not access.get("allowed"):
            raise PermissionError(access.get("reason") or "finance_execution_not_authorised")
        return record

    def record_response(self, workspace_id: str, export_id: str, response: dict[str, Any]) -> dict[str, Any]:
        record = self.load(workspace_id, export_id)
        rows = response.get("Invoices") or []; item = rows[0] if rows else {}
        if item.get("HasErrors") or not item.get("InvoiceID"):
            record["execution"] = {"received_at": _now(), "resource_id": None,
                                   "validation_errors": item.get("ValidationErrors") or [],
                                   "provider_response_hash": canonical_contract_hash(response)}
            record["status"] = "provider_rejected"; self._rehash_save(workspace_id, record)
            raise ValueError("xero_provider_did_not_create_sales_invoice")
        record["execution"] = {"received_at": _now(), "resource_id": item["InvoiceID"],
                               "resource_status": item.get("Status"),
                               "provider_response_hash": canonical_contract_hash(response),
                               "idempotency_key": record["idempotency_key"]}
        record["status"] = "provider_response_received"; record["external_write_performed"] = True
        self._rehash_save(workspace_id, record); return record

    def verify(self, workspace_id: str, export_id: str, response: dict[str, Any]) -> dict[str, Any]:
        record = self.load(workspace_id, export_id); resource_id = record["execution"]["resource_id"]
        item = next((row for row in response.get("Invoices") or [] if row.get("InvoiceID") == resource_id), None)
        expected = record["payload"]["Invoices"][0]; errors: list[str] = []
        if not item:
            errors.append("created_resource_not_returned")
        else:
            checks = [
                (item.get("Type") == "ACCREC", "type_mismatch"),
                (item.get("InvoiceNumber") == expected.get("InvoiceNumber"), "invoice_number_mismatch"),
                (item.get("Status") == expected.get("Status"), "status_mismatch"),
                ((item.get("Contact") or {}).get("ContactID") == (expected.get("Contact") or {}).get("ContactID"), "contact_mismatch"),
                (abs(_money(item.get("Total")) - sum(_money(x.get("UnitAmount")) * _money(x.get("Quantity")) + _money(x.get("TaxAmount")) for x in expected.get("LineItems") or [])) <= 0.02, "total_mismatch"),
            ]
            errors.extend(code for ok, code in checks if not ok)
        record["verification"] = {"verified_at": _now(), "resource_id": resource_id,
                                  "provider_readback_hash": canonical_contract_hash(response), "errors": errors}
        record["status"] = "verification_failed" if errors else "verified_in_xero"
        self._rehash_save(workspace_id, record)
        if errors:
            raise ValueError("xero_sales_invoice_readback_failed:" + ",".join(errors))
        self._project(workspace_id, record)
        return record

    def load(self, workspace_id: str, export_id: str) -> dict[str, Any]:
        path = self._dir(workspace_id) / f"{_safe(export_id)}.json"
        if not path.exists(): raise FileNotFoundError(export_id)
        record = json.loads(path.read_text(encoding="utf-8")); expected = record.get("export_hash")
        payload = dict(record); payload.pop("export_hash", None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError("xero_sales_invoice_export_hash_mismatch")
        if record.get("workspace_id") != workspace_id:
            raise PermissionError("xero_sales_invoice_workspace_isolation_violation")
        return record

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load(workspace_id, path.stem) for path in sorted(
            self._dir(workspace_id).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)]

    def for_invoice(self, workspace_id: str, invoice_id: str) -> dict[str, Any] | None:
        return next((row for row in self.list(workspace_id) if row.get("invoice_id") == invoice_id), None)

    def _project(self, workspace_id: str, record: dict[str, Any]) -> None:
        draft = self.bookkeeping.load(workspace_id, self.sales.load_invoice(workspace_id, record["invoice_id"])["bookkeeping_draft_id"])
        draft.setdefault("provider_exports", {})["xero"] = {
            "export_id": record["export_id"], "resource_id": record["verification"]["resource_id"],
            "verified_at": record["verification"]["verified_at"], "status": "verified_in_xero",
            "payload_hash": record["payload_hash"],
        }
        draft["status"] = "synced_to_xero"; draft.pop("draft_hash", None); draft["draft_hash"] = canonical_contract_hash(draft)
        self.bookkeeping._save_draft(workspace_id, draft)
        self.sales.mark_verified_provider(workspace_id, record["invoice_id"], provider="xero", export_summary={
            "export_id": record["export_id"], "resource_id": record["verification"]["resource_id"],
            "verified_at": record["verification"]["verified_at"], "payload_hash": record["payload_hash"],
            "status": "verified_in_xero", "target_status": record["target_status"],
        })

    def _dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/xero_sales_invoice_exports"
        path.mkdir(parents=True, exist_ok=True); return path

    def _rehash_save(self, workspace_id: str, record: dict[str, Any]) -> None:
        record.pop("export_hash", None); record["export_hash"] = canonical_contract_hash(record)
        (self._dir(workspace_id) / f"{_safe(record['export_id'])}.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
