"""Canonical, read-only Finance ledger built from provider evidence.

The ledger is intentionally stored beside the Business Financial Model. Raw Xero
evidence remains immutable; normalized records carry source references and hashes.
No method in this service can write to an accounting provider.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_bank_activity_service import FinanceBankActivityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _number(value: Any) -> float:
    try:
        return round(float(value or 0), 4)
    except (TypeError, ValueError):
        return 0.0


def _day(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("/Date("):
        try:
            millis = int(text.split("(", 1)[1].split("+", 1)[0].split("-", 1)[0].rstrip(")"))
            return datetime.fromtimestamp(millis / 1000, UTC).date().isoformat()
        except (ValueError, IndexError, OSError):
            return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return text[:10] or None


def _contact(value: Any) -> dict[str, Any]:
    record = value if isinstance(value, dict) else {}
    return {
        "contact_id": record.get("ContactID"),
        "display_name": record.get("Name"),
    }


def _source_ref(sync_id: str, collection: str, provider_id: Any) -> dict[str, Any]:
    return {
        "provider": "xero",
        "sync_id": sync_id,
        "collection": collection,
        "provider_id": provider_id,
        "verification_status": "provider_sourced",
    }


def _line_items(value: Any, limit: int = 100) -> list[dict[str, Any]]:
    rows = []
    for item in list(value or [])[:limit]:
        if not isinstance(item, dict):
            continue
        rows.append({
            "description": item.get("Description"),
            "quantity": _number(item.get("Quantity")),
            "unit_amount": _number(item.get("UnitAmount")),
            "line_amount": _number(item.get("LineAmount")),
            "account_code": item.get("AccountCode"),
            "tax_type": item.get("TaxType"),
            "tracking": [
                {"name": option.get("Name"), "option": option.get("Option")}
                for option in (item.get("Tracking") or []) if isinstance(option, dict)
            ],
        })
    return rows


class FinanceLedgerService:
    """Normalize the latest read-only Xero sync into a hash-bound local ledger."""

    COLLECTIONS = {
        "accounts": "Accounts",
        "invoices": "Invoices",
        "bank_transactions": "BankTransactions",
        "payments": "Payments",
        "manual_journals": "ManualJournals",
        "tracking_categories": "TrackingCategories",
        "projects": "Projects",
    }

    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()

    def build(self, workspace_id: str, *, created_by: str = "finance_pilot",
              created_at: str | None = None) -> dict[str, Any]:
        model = self.repository.load_dict(workspace_id, "business_financial_model")
        xero = (model.get("integration_evidence") or {}).get("xero") or {}
        evidence_ref = xero.get("evidence_ref") or {}
        sync_id = str(evidence_ref.get("sync_id") or xero.get("sync_id") or "")
        if not sync_id:
            raise FileNotFoundError("A completed Xero sync is required before building the Finance ledger.")
        sync_dir = AIONBusinessPaths.business_container_dir(workspace_id) / "integrations/xero/syncs" / sync_id
        snapshot_path = sync_dir / "snapshot.json"
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Xero snapshot not found: {sync_id}")
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        expected_snapshot_hash = snapshot.get("snapshot_hash")
        unhashed = dict(snapshot); unhashed.pop("snapshot_hash", None)
        if not expected_snapshot_hash or expected_snapshot_hash != self._hash(unhashed):
            raise ValueError("xero_snapshot_hash_mismatch")

        raw = {
            name: self._read_collection(sync_dir / f"{name}.json", root)
            for name, root in self.COLLECTIONS.items()
        }
        records = {
            "accounts": [self._account(item, sync_id) for item in raw["accounts"]],
            "invoices": [self._invoice(item, sync_id) for item in raw["invoices"]],
            "bank_transactions": [self._bank_transaction(item, sync_id) for item in raw["bank_transactions"]],
            "payments": [self._payment(item, sync_id) for item in raw["payments"]],
            "manual_journals": [self._manual_journal(item, sync_id) for item in raw["manual_journals"]],
            "tracking_categories": [self._tracking(item, sync_id) for item in raw["tracking_categories"]],
            "projects": [self._project_record(item, sync_id) for item in raw["projects"]],
        }
        canonical_bank_activity = FinanceBankActivityService(self.repository).ledger_records(workspace_id)
        controlled_test_bank_activity = [
            item for item in canonical_bank_activity
            if (item.get("source_ref") or {}).get("verification_status") == "controlled_test_fixture"
        ]
        existing_bank_ids = {str(item.get("bank_transaction_id")) for item in records["bank_transactions"]}
        records["bank_transactions"].extend(
            item for item in canonical_bank_activity
            if str(item.get("bank_transaction_id")) not in existing_bank_ids
        )
        for collection, items in records.items():
            for item in items:
                item["record_hash"] = canonical_contract_hash(item)
            self._write_jsonl(workspace_id, sync_id, collection, items)

        invoices = records["invoices"]
        receivables = [item for item in invoices if item["invoice_type"] == "sales_invoice"]
        payables = [item for item in invoices if item["invoice_type"] == "supplier_bill"]
        ledger_id = f"finance-ledger-{_safe(sync_id)}"
        ledger = {
            "schema_version": "aion.finance.ledger.v1",
            "ledger_id": ledger_id,
            "workspace_id": workspace_id,
            "provider": "xero_plus_canonical_bank_activity" if canonical_bank_activity else "xero",
            "source_sync_id": sync_id,
            "source_snapshot_hash": expected_snapshot_hash,
            "created_at": created_at or _now(),
            "created_by": created_by,
            "read_only": True,
            "external_write_performed": False,
            "currency": model.get("currency") or "EUR",
            "period": snapshot.get("period") or {},
            "record_counts": {key: len(value) for key, value in records.items()},
            "canonical_bank_activity_count": len(canonical_bank_activity),
            "controlled_test_bank_activity_count": len(controlled_test_bank_activity),
            "provider_bank_transaction_count": len(raw["bank_transactions"]),
            "summaries": {
                "accounts_receivable": round(sum(item["amount_due"] for item in receivables), 2),
                "accounts_payable": round(sum(item["amount_due"] for item in payables), 2),
                "overdue_receivables": round(sum(item["amount_due"] for item in receivables if item["is_overdue"]), 2),
                "overdue_payables": round(sum(item["amount_due"] for item in payables if item["is_overdue"]), 2),
                "bank_transaction_total": round(sum(
                    item["total"] for item in records["bank_transactions"]
                    if (item.get("source_ref") or {}).get("verification_status") != "controlled_test_fixture"
                ), 2),
                "controlled_test_bank_transaction_total": round(sum(
                    item["total"] for item in controlled_test_bank_activity
                ), 2),
                "payment_total": round(sum(item["amount"] for item in records["payments"]), 2),
            },
            "collections": {
                key: f"finance/ledger/{ledger_id}/{key}.jsonl" for key in records
            },
            "warnings": [
                f"{name.replace('_', ' ').title()} were not returned by this Xero sync."
                for name, items in records.items() if not items
            ] + (["Bank Transactions were not returned by this Xero sync; controlled test evidence is excluded from actuals."]
                 if not raw["bank_transactions"] and canonical_bank_activity else []),
        }
        ledger["ledger_hash"] = canonical_contract_hash(ledger)
        path = self._dir(workspace_id, ledger_id) / "ledger.json"
        path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._index(workspace_id, ledger, path)
        self._project(workspace_id, model, ledger, path)
        return ledger

    def latest(self, workspace_id: str, *, include_records: bool = False,
               limits: dict[str, int] | None = None) -> dict[str, Any] | None:
        root = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/ledger"
        paths = sorted(root.glob("*/ledger.json"), key=lambda item: item.stat().st_mtime, reverse=True) if root.exists() else []
        if not paths:
            return None
        ledger = json.loads(paths[0].read_text(encoding="utf-8")); self._verify(ledger)
        if include_records:
            bounded = limits or {}
            ledger["records"] = {
                name: self.records(workspace_id, ledger["ledger_id"], name, limit=min(max(int(bounded.get(name, 200)), 1), 1000))
                for name in self.COLLECTIONS
            }
        return ledger

    def records(self, workspace_id: str, ledger_id: str, collection: str, *, limit: int = 200,
                offset: int = 0) -> list[dict[str, Any]]:
        if collection not in self.COLLECTIONS:
            raise ValueError("invalid_finance_ledger_collection")
        path = self._dir(workspace_id, ledger_id) / f"{collection}.jsonl"
        if not path.exists():
            return []
        result = []
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            if index < offset:
                continue
            if len(result) >= min(max(limit, 1), 1000):
                break
            record = json.loads(line)
            expected = record.get("record_hash"); payload = dict(record); payload.pop("record_hash", None)
            if not expected or canonical_contract_hash(payload) != expected:
                raise ValueError("finance_ledger_record_hash_mismatch")
            result.append(record)
        return result

    def _dir(self, workspace_id: str, ledger_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/ledger" / _safe(ledger_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_jsonl(self, workspace_id: str, sync_id: str, collection: str,
                     records: Iterable[dict[str, Any]]) -> None:
        ledger_id = f"finance-ledger-{_safe(sync_id)}"
        path = self._dir(workspace_id, ledger_id) / f"{collection}.jsonl"
        path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in records), encoding="utf-8")

    @staticmethod
    def _read_collection(path: Path, root: str) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        value = json.loads(path.read_text(encoding="utf-8"))
        records = value.get(root) if isinstance(value, dict) else []
        if root == "Projects" and isinstance(value, dict) and not records:
            records = value.get("items") or []
        return [item for item in (records or []) if isinstance(item, dict)]

    @staticmethod
    def _hash(value: Any) -> str:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _account(item: dict[str, Any], sync_id: str) -> dict[str, Any]:
        provider_id = item.get("AccountID")
        return {"account_id": provider_id, "code": item.get("Code"), "name": item.get("Name"),
                "type": item.get("Type"), "status": item.get("Status"), "currency": item.get("CurrencyCode"),
                "bank_account_type": item.get("BankAccountType"), "source_ref": _source_ref(sync_id, "accounts", provider_id)}

    @staticmethod
    def _invoice(item: dict[str, Any], sync_id: str) -> dict[str, Any]:
        provider_id = item.get("InvoiceID"); invoice_type = str(item.get("Type") or "")
        due = _number(item.get("AmountDue")); due_date = _day(item.get("DueDate"))
        return {"invoice_id": provider_id, "invoice_number": item.get("InvoiceNumber"),
                "invoice_type": "sales_invoice" if invoice_type == "ACCREC" else "supplier_bill" if invoice_type == "ACCPAY" else invoice_type.lower(),
                "status": item.get("Status"), "contact": _contact(item.get("Contact")), "date": _day(item.get("Date")),
                "due_date": due_date, "currency": item.get("CurrencyCode"), "subtotal": _number(item.get("SubTotal")),
                "tax": _number(item.get("TotalTax")), "total": _number(item.get("Total")), "amount_paid": _number(item.get("AmountPaid")),
                "amount_credited": _number(item.get("AmountCredited")), "amount_due": due,
                "line_items": _line_items(item.get("LineItems")),
                "reference": item.get("Reference"), "is_overdue": bool(due > 0 and due_date and due_date < date.today().isoformat()),
                "source_ref": _source_ref(sync_id, "invoices", provider_id)}

    @staticmethod
    def _bank_transaction(item: dict[str, Any], sync_id: str) -> dict[str, Any]:
        provider_id = item.get("BankTransactionID")
        return {"bank_transaction_id": provider_id, "transaction_type": str(item.get("Type") or "").lower(),
                "status": item.get("Status"), "contact": _contact(item.get("Contact")), "date": _day(item.get("Date")),
                "reference": item.get("Reference"), "currency": item.get("CurrencyCode"), "subtotal": _number(item.get("SubTotal")),
                "tax": _number(item.get("TotalTax")), "total": _number(item.get("Total")),
                "line_items": _line_items(item.get("LineItems")),
                "bank_account_id": (item.get("BankAccount") or {}).get("AccountID"), "is_reconciled": bool(item.get("IsReconciled")),
                "source_ref": _source_ref(sync_id, "bank_transactions", provider_id)}

    @staticmethod
    def _payment(item: dict[str, Any], sync_id: str) -> dict[str, Any]:
        provider_id = item.get("PaymentID"); invoice = item.get("Invoice") or {}
        return {"payment_id": provider_id, "date": _day(item.get("Date")), "amount": _number(item.get("Amount")),
                "currency_rate": _number(item.get("CurrencyRate")) or 1.0, "status": item.get("Status"),
                "reference": item.get("Reference"), "invoice_id": invoice.get("InvoiceID"),
                "invoice_number": invoice.get("InvoiceNumber"), "account_id": (item.get("Account") or {}).get("AccountID"),
                "source_ref": _source_ref(sync_id, "payments", provider_id)}

    @staticmethod
    def _manual_journal(item: dict[str, Any], sync_id: str) -> dict[str, Any]:
        provider_id = item.get("ManualJournalID")
        lines = item.get("JournalLines") or []
        return {"manual_journal_id": provider_id, "date": _day(item.get("Date")), "status": item.get("Status"),
                "narration": item.get("Narration"), "line_count": len(lines),
                "net_amount": round(sum(_number(line.get("LineAmount")) for line in lines if isinstance(line, dict)), 4),
                "source_ref": _source_ref(sync_id, "manual_journals", provider_id)}

    @staticmethod
    def _tracking(item: dict[str, Any], sync_id: str) -> dict[str, Any]:
        provider_id = item.get("TrackingCategoryID")
        return {"tracking_category_id": provider_id, "name": item.get("Name"), "status": item.get("Status"),
                "options": [{"option_id": opt.get("TrackingOptionID"), "name": opt.get("Name"), "status": opt.get("Status")} for opt in (item.get("Options") or []) if isinstance(opt, dict)],
                "source_ref": _source_ref(sync_id, "tracking_categories", provider_id)}

    @staticmethod
    def _project_record(item: dict[str, Any], sync_id: str) -> dict[str, Any]:
        provider_id = item.get("projectId") or item.get("ProjectID")
        return {"project_id": provider_id, "name": item.get("name") or item.get("Name"), "status": item.get("status") or item.get("Status"),
                "contact_id": item.get("contactId") or (item.get("Contact") or {}).get("ContactID"),
                "estimate_amount": _number(item.get("estimateAmount") or item.get("EstimateAmount")),
                "source_ref": _source_ref(sync_id, "projects", provider_id)}

    def _index(self, workspace_id: str, ledger: dict[str, Any], path: Path) -> None:
        tree = WorkflowFileCabinetRepository.load(workspace_id)
        folders = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        finance = next((item for item in folders if item.get("id") == "folder_finance"), None)
        if finance is None:
            finance = {"id": "folder_finance", "name": "Finance", "type": "department", "children": []}; folders.append(finance)
        children = finance.setdefault("children", [])
        ledgers = next((item for item in children if item.get("id") == "folder_finance_ledgers"), None)
        if ledgers is None:
            ledgers = {"id": "folder_finance_ledgers", "name": "Ledgers", "type": "folder", "children": []}; children.append(ledgers)
        ledgers.setdefault("children", []).append({"id": f"finance_ledger_pointer_{ledger['ledger_id']}", "name": ledger["ledger_id"],
            "type": "business_container_artifact", "document_type": "finance_ledger", "status": "read_only_provider_sourced",
            "target": {"storage_path": str(path), "ledger_hash": ledger["ledger_hash"], "record_counts": ledger["record_counts"]}})
        tree["folders"] = folders; tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}
        WorkflowFileCabinetRepository.save(workspace_id, tree)

    def _project(self, workspace_id: str, model: dict[str, Any], ledger: dict[str, Any], path: Path) -> None:
        model["ledger"] = {"ledger_id": ledger["ledger_id"], "ledger_hash": ledger["ledger_hash"], "storage_path": str(path),
                           "source_sync_id": ledger["source_sync_id"], "record_counts": ledger["record_counts"],
                           "summaries": ledger["summaries"], "read_only": True}
        model["revision"] = int(model.get("revision") or 0) + 1
        self.repository.save_dict(workspace_id, "business_financial_model", model)
        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            intelligence.setdefault("departments", {}).setdefault("finance", {})["ledger"] = model["ledger"]
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1
            self.repository.save_dict(workspace_id, "department_intelligence", intelligence)

    @staticmethod
    def _verify(ledger: dict[str, Any]) -> None:
        expected = ledger.get("ledger_hash"); payload = dict(ledger); payload.pop("ledger_hash", None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError("finance_ledger_hash_mismatch")
