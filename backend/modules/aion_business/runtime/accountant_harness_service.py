"""Provider-neutral accountant harness.

The harness turns provider evidence into the same hash-bound Finance ledger used
by the existing Xero reconciliation engine.  It is deliberately read-only: an
adapter may expose future write capabilities, but no write can occur here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.providers.accounting_provider_contract import CANONICAL_COLLECTIONS
from backend.modules.aion_business.providers.freeagent_accounting_adapter import FreeAgentAccountingAdapter
from backend.modules.aion_business.providers.freshbooks_accounting_adapter import FreshBooksAccountingAdapter
from backend.modules.aion_business.providers.quickbooks_online_accounting_adapter import QuickBooksOnlineAccountingAdapter
from backend.modules.aion_business.providers.sage_accounting_adapter import SageAccountingAdapter
from backend.modules.aion_business.providers.zoho_books_accounting_adapter import ZohoBooksAccountingAdapter
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_transaction_reconciliation_service import FinanceTransactionReconciliationService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


class AccountantHarnessService:
    """Sync, normalize and reconcile without giving an LLM ledger authority."""

    ADAPTERS = {
        "quickbooks_online": QuickBooksOnlineAccountingAdapter,
        "sage_accounting": SageAccountingAdapter,
        "freeagent": FreeAgentAccountingAdapter,
        "freshbooks": FreshBooksAccountingAdapter,
        "zoho_books": ZohoBooksAccountingAdapter,
    }

    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()

    def catalog(self) -> dict[str, Any]:
        providers = [
            {
                "provider_id": "xero", "label": "Xero", "implementation": "existing_live_adapter",
                "uses_shared_accountant_controls": True, "bank_reconciliation_api": False,
                "boundary": "Bank-statement reconciliation remains an approved manual Xero handoff.",
            },
            *[
                {
                    **factory().capabilities().to_dict(),
                    "implementation": "read_adapter_and_canonical_harness_ready",
                    "uses_shared_accountant_controls": True,
                    "boundary": "Connection credentials and provider sandbox verification are still required before live use.",
                }
                for factory in self.ADAPTERS.values()
            ],
        ]
        return {
            "schema_version": "aion.finance.accountant_harness_catalog.v1",
            "providers": providers,
            "provider_count": len(providers),
            "control_plane": {
                "normalization": "provider facts become a canonical read-only ledger",
                "matching": "deterministic amount, reference, counterparty and date evidence",
                "judgement": "ambiguous tax or account treatment is escalated, never invented",
                "writes": "exact payload approval, idempotency and provider read-back are mandatory",
                "tax_boundary": "Tessaris does not file tax returns or claim regulated accountant status",
            },
        }

    async def sync(self, workspace_id: str, provider_id: str, *, access_token: str,
                   company_id: str, actor: str = "finance_pilot", sandbox: bool = False) -> dict[str, Any]:
        factory = self.ADAPTERS.get(provider_id)
        if factory is None:
            raise ValueError("accounting_provider_read_adapter_not_available")
        adapter = factory()
        raw = await adapter.read_snapshot(access_token=access_token, company_id=company_id, sandbox=sandbox)
        return self.ingest(workspace_id, provider_id, raw, company_id=company_id, actor=actor)

    def ingest(self, workspace_id: str, provider_id: str, raw: dict[str, Any], *,
               company_id: str, actor: str = "finance_pilot", occurred_at: str | None = None) -> dict[str, Any]:
        factory = self.ADAPTERS.get(provider_id)
        if factory is None:
            raise ValueError("accounting_provider_read_adapter_not_available")
        occurred_at = occurred_at or _now()
        sync_id = f"{provider_id}-sync-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
        adapter = factory()
        records = adapter.normalize_snapshot(raw, sync_id=sync_id, company_id=company_id)
        if set(records) != set(CANONICAL_COLLECTIONS):
            raise ValueError("accounting_adapter_canonical_collection_mismatch")
        raw_hash = self._hash(raw)
        sync_dir = self._integration_dir(workspace_id, provider_id) / "syncs" / sync_id
        sync_dir.mkdir(parents=True, exist_ok=True)
        evidence = {
            "schema_version": "aion.finance.accounting_provider_sync.v1", "sync_id": sync_id,
            "workspace_id": workspace_id, "provider": provider_id, "company_id": company_id,
            "occurred_at": occurred_at, "actor": actor, "read_only": True,
            "raw_snapshot_hash": raw_hash, "record_counts": {key: len(value) for key, value in records.items()},
            "external_write_performed": False,
        }
        evidence["sync_hash"] = canonical_contract_hash(evidence)
        (sync_dir / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (sync_dir / "raw_snapshot.json").write_text(json.dumps(raw, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        ledger = self._write_ledger(workspace_id, provider_id, sync_id, raw_hash, records, actor, occurred_at)
        self._project(workspace_id, provider_id, evidence, ledger)
        return {"sync": evidence, "ledger": ledger}

    def reconcile(self, workspace_id: str, *, actor: str = "finance_pilot",
                  amount_tolerance: float = 0.01, date_window_days: int = 7) -> dict[str, Any]:
        return FinanceTransactionReconciliationService(self.repository).run(
            workspace_id, created_by=actor, amount_tolerance=amount_tolerance,
            date_window_days=date_window_days,
        )

    def _write_ledger(self, workspace_id: str, provider_id: str, sync_id: str,
                      raw_hash: str, records: dict[str, list[dict[str, Any]]],
                      actor: str, occurred_at: str) -> dict[str, Any]:
        ledger_id = f"finance-ledger-{_safe(sync_id)}"
        root = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/ledger" / ledger_id
        root.mkdir(parents=True, exist_ok=True)
        for collection, rows in records.items():
            with (root / f"{collection}.jsonl").open("w", encoding="utf-8") as stream:
                for row in rows:
                    value = dict(row); value["record_hash"] = canonical_contract_hash(value)
                    stream.write(json.dumps(value, sort_keys=True, default=str) + "\n")
        invoices = records["invoices"]
        receivables = [row for row in invoices if row.get("invoice_type") == "sales_invoice"]
        payables = [row for row in invoices if row.get("invoice_type") == "supplier_bill"]
        ledger = {
            "schema_version": "aion.finance.ledger.v1", "ledger_id": ledger_id,
            "workspace_id": workspace_id, "provider": provider_id, "source_sync_id": sync_id,
            "source_snapshot_hash": raw_hash, "created_at": occurred_at, "created_by": actor,
            "read_only": True, "external_write_performed": False, "currency": None, "period": {},
            "record_counts": {key: len(value) for key, value in records.items()},
            "canonical_bank_activity_count": 0, "controlled_test_bank_activity_count": 0,
            "provider_bank_transaction_count": len(records["bank_transactions"]),
            "summaries": {
                "accounts_receivable": round(sum(float(row.get("amount_due") or 0) for row in receivables), 2),
                "accounts_payable": round(sum(float(row.get("amount_due") or 0) for row in payables), 2),
                "overdue_receivables": round(sum(float(row.get("amount_due") or 0) for row in receivables if row.get("is_overdue")), 2),
                "overdue_payables": round(sum(float(row.get("amount_due") or 0) for row in payables if row.get("is_overdue")), 2),
                "bank_transaction_total": round(sum(float(row.get("total") or 0) for row in records["bank_transactions"]), 2),
                "controlled_test_bank_transaction_total": 0.0,
                "payment_total": round(sum(float(row.get("amount") or 0) for row in records["payments"]), 2),
            },
            "collections": {key: f"finance/ledger/{ledger_id}/{key}.jsonl" for key in records},
            "warnings": [f"{key.replace('_', ' ').title()} were not returned by this {provider_id} sync." for key, value in records.items() if not value],
        }
        ledger["ledger_hash"] = canonical_contract_hash(ledger)
        path = root / "ledger.json"
        path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._index(workspace_id, ledger, path)
        return ledger

    def _project(self, workspace_id: str, provider_id: str, evidence: dict[str, Any], ledger: dict[str, Any]) -> None:
        model = self.repository.load_optional_dict(workspace_id, "business_financial_model") or {
            "schema_version": "aion.business_financial_model.v1", "workspace_id": workspace_id, "revision": 0
        }
        integrations = model.setdefault("integration_evidence", {})
        integrations[provider_id] = {"status": "synced", "sync_id": evidence["sync_id"], "sync_hash": evidence["sync_hash"],
                                    "record_counts": evidence["record_counts"], "read_only": True}
        model["ledger"] = {"ledger_id": ledger["ledger_id"], "ledger_hash": ledger["ledger_hash"],
                           "source_sync_id": ledger["source_sync_id"], "provider": provider_id,
                           "record_counts": ledger["record_counts"], "summaries": ledger["summaries"], "read_only": True}
        model["revision"] = int(model.get("revision") or 0) + 1
        self.repository.save_dict(workspace_id, "business_financial_model", model)

    def _index(self, workspace_id: str, ledger: dict[str, Any], path: Path) -> None:
        tree = WorkflowFileCabinetRepository.load(workspace_id)
        folders = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        finance = next((item for item in folders if item.get("id") == "folder_finance"), None)
        if finance is None:
            finance = {"id": "folder_finance", "name": "Finance", "type": "department", "children": []}; folders.append(finance)
        ledgers = next((item for item in finance.setdefault("children", []) if item.get("id") == "folder_finance_ledgers"), None)
        if ledgers is None:
            ledgers = {"id": "folder_finance_ledgers", "name": "Ledgers", "type": "folder", "children": []}; finance["children"].append(ledgers)
        ledgers.setdefault("children", []).append({
            "id": f"finance_ledger_pointer_{ledger['ledger_id']}", "name": ledger["ledger_id"],
            "type": "business_container_artifact", "document_type": "finance_ledger", "status": "read_only_provider_sourced",
            "target": {"storage_path": str(path), "ledger_hash": ledger["ledger_hash"], "provider": ledger["provider"]},
        })
        tree["folders"] = folders
        tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}
        WorkflowFileCabinetRepository.save(workspace_id, tree)

    @staticmethod
    def _integration_dir(workspace_id: str, provider_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "integrations" / _safe(provider_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _hash(value: Any) -> str:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()
