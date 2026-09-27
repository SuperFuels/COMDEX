"""Provider-neutral, approval-gated bookkeeping from accepted Finance evidence.

The internal journal is the accounting control plane. Provider adapters may
translate an approved entry, but cannot change its lines or approval hash.
This module never files tax returns or performs an external provider write.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
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


PROVIDERS: dict[str, dict[str, Any]] = {
    "xero": {
        "name": "Xero", "live_connector": True, "implemented_mode": "read_only_sync",
        "available_reads": ["chart_of_accounts", "invoices", "bills", "payments", "bank_transactions", "journals", "reports"],
        "available_writes": [], "reconciliation_mode": "approved_manual_handoff",
    },
    "quickbooks_online": {
        "name": "QuickBooks Online", "live_connector": False, "implemented_mode": "read_adapter_and_harness_ready",
        "available_reads": ["chart_of_accounts", "invoices", "bills", "payments", "purchases", "journals"],
        "available_writes": [], "reconciliation_mode": "local_review_only_until_connected",
    },
    "sage_accounting": {
        "name": "Sage Business Cloud Accounting", "live_connector": False, "implemented_mode": "read_adapter_and_harness_ready",
        "available_reads": ["chart_of_accounts", "sales_invoices", "purchase_invoices", "payments", "bank_transactions", "journals"],
        "available_writes": [], "reconciliation_mode": "local_review_only_until_connected",
    },
    "freeagent": {
        "name": "FreeAgent", "live_connector": False, "implemented_mode": "adapter_contract_ready",
        "available_reads": [], "available_writes": [], "reconciliation_mode": "not_connected",
    },
    "generic_import": {
        "name": "Spreadsheet / canonical import", "live_connector": True, "implemented_mode": "reviewed_import",
        "available_reads": ["accepted_finance_artifacts"], "available_writes": [],
        "reconciliation_mode": "local_review_only",
    },
}


class FinanceBookkeepingService:
    """Prepare, separately approve, and post balanced internal journals."""

    def __init__(self, repository: BusinessContainerRepository | None = None,
                 authority: OrganizationAuthorityService | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = authority or OrganizationAuthorityService(self.repository)

    def provider_catalog(self, workspace_id: str) -> dict[str, Any]:
        financial = self.repository.load_optional_dict(workspace_id, "business_financial_model") or {}
        integrations = financial.get("integration_evidence") or {}
        providers = []
        for provider_id, definition in PROVIDERS.items():
            evidence = integrations.get(provider_id) or {}
            connection: dict[str, Any] = {}
            if provider_id == "xero":
                path = AIONBusinessPaths.business_container_dir(workspace_id) / "integrations/xero/connection.json"
                if path.exists():
                    connection = json.loads(path.read_text(encoding="utf-8"))
            connected = bool(provider_id == "generic_import" or connection.get("status") == "connected" or evidence.get("status") == "connected")
            write_scopes = {"accounting.contacts", "accounting.invoices", "accounting.payments", "accounting.banktransactions",
                            "accounting.manualjournals", "accounting.attachments"}
            write_enabled = bool(provider_id == "xero" and connection.get("status") == "connected"
                                 and write_scopes.issubset(set(connection.get("scopes") or [])))
            available_writes = [
                "exact_approved_accounts_payable_bill",
                "exact_approved_accounts_receivable_invoice",
            ] if write_enabled else list(definition["available_writes"])
            providers.append({
                "provider_id": provider_id, **definition, "connected": connected,
                "status": "connected" if connected else "not_connected",
                "implemented_mode": "exact_approved_write_and_readback" if write_enabled else definition["implemented_mode"],
                "available_writes": available_writes, "external_writes_enabled": write_enabled,
                "boundary": (
                    "Only an exact-approved Xero bill or sales invoice may be written and it is not "
                    "confirmed until the created resource is read back."
                    if write_enabled else "Provider writes remain disabled until an exact approved payload "
                    "adapter is implemented, authorised and live-tested for this provider."
                ),
            })
        return {
            "schema_version": "aion.finance.accounting_provider_catalog.v1",
            "workspace_id": workspace_id, "providers": providers,
            "canonical_instruction_schema": "aion.finance.accounting_instruction.v1",
            "canonical_journal_schema": "aion.finance.bookkeeping_journal.v1",
            "provider_neutral_bookkeeping_ready": True,
            "external_writes_enabled": any(row["external_writes_enabled"] for row in providers),
        }

    def prepare_document(self, workspace_id: str, document_id: str, *, prepared_by_person_id: str) -> dict[str, Any]:
        access = self.authority.access_decision(
            workspace_id, person_id=prepared_by_person_id, capability="finance.prepare"
        )
        if not access.get("allowed"):
            raise PermissionError(access.get("reason") or "finance_prepare_not_authorised")
        inbox = self.repository.load_dict(workspace_id, "finance_inbox")
        document = next((row for row in inbox.get("documents") or [] if row.get("id") == document_id), None)
        if not document:
            raise FileNotFoundError(f"Finance document not found: {document_id}")
        if document.get("status") != "approved_for_accounting":
            raise ValueError("approved_finance_document_required")
        accounting = document.get("accounting") or {}
        instruction = accounting.get("exact_payload") or {}
        if not instruction or accounting.get("payload_hash") != self._instruction_hash(instruction):
            raise ValueError("finance_accounting_instruction_hash_mismatch")

        fields = instruction.get("fields") or {}
        allocation = instruction.get("allocation") or {}
        ownership = instruction.get("ownership") or {}
        total, net, tax = (_money(fields.get(key)) for key in ("total", "net", "tax"))
        if total <= 0:
            raise ValueError("positive_accounting_total_required")
        if net <= 0:
            net = round(total - tax, 2) if tax > 0 else total
        if abs(round(net + tax - total, 2)) > 0.02:
            raise ValueError("accounting_amounts_do_not_balance")

        expense_account = str(allocation.get("account_code") or "").strip()
        unresolved = []
        if not expense_account:
            unresolved.append("expense_account_code")
        tax_code = str(allocation.get("tax_code") or "").strip()
        if tax > 0 and not tax_code:
            unresolved.append("input_tax_code")
        destination = str(instruction.get("destination") or "expense")
        payment_method = str(fields.get("payment_method") or "").casefold()
        if destination == "supplier_bill":
            credit_account = "control.trade_payables"
        elif ownership.get("card_asset_id") or "card" in payment_method:
            credit_account = "control.company_card_clearing"
        elif any(word in payment_method for word in ("cash", "bank", "debit")):
            credit_account = "control.bank_clearing"
        else:
            credit_account = "control.unallocated_payment"
            unresolved.append("payment_control_account")

        lines = []
        if net:
            lines.append(self._line(expense_account or "unresolved.expense", "debit", net,
                                    allocation.get("account_name") or "Expense awaiting account mapping",
                                    account_type="expense"))
        if tax:
            lines.append(self._line("control.input_tax", "debit", tax, "Input tax",
                                    tax_code=tax_code or None, account_type="asset"))
        control_type = "asset" if credit_account == "control.bank_clearing" else "liability"
        lines.append(self._line(credit_account, "credit", total, self._control_label(credit_account),
                                account_type=control_type))
        debit_total = round(sum(row["debit"] for row in lines), 2)
        credit_total = round(sum(row["credit"] for row in lines), 2)
        if debit_total != credit_total:
            raise ValueError("bookkeeping_journal_unbalanced")

        draft_id = f"bookkeeping-{_safe(document_id)}"
        draft = {
            "schema_version": "aion.finance.bookkeeping_journal.v1",
            "draft_id": draft_id, "workspace_id": workspace_id,
            "source_document_id": document_id,
            "source_document_hash": instruction.get("source_document_hash"),
            "instruction_hash": accounting["payload_hash"],
            "journal_date": fields.get("document_date"),
            "currency": fields.get("currency") or "EUR",
            "description": fields.get("description") or fields.get("supplier") or document.get("document_type"),
            "counterparty": fields.get("supplier"), "document_type": document.get("document_type"),
            "destination": destination, "department_id": ownership.get("department_id"),
            "project_id": ownership.get("project_id"), "lines": lines,
            "debit_total": debit_total, "credit_total": credit_total,
            "unresolved_controls": sorted(set(unresolved)),
            "status": "mapping_required" if unresolved else "exact_posting_approval_required",
            "prepared_by_person_id": prepared_by_person_id, "prepared_at": _now(),
            "posting_approval": None, "internal_posting": None,
            "external_write_performed": False,
        }
        draft["draft_hash"] = canonical_contract_hash(draft)
        self._save_draft(workspace_id, draft)
        return draft

    def approve(self, workspace_id: str, draft_id: str, *, approved_by_person_id: str,
                approved_draft_hash: str) -> dict[str, Any]:
        draft = self.load(workspace_id, draft_id)
        if draft.get("unresolved_controls"):
            raise ValueError("bookkeeping_mapping_required_before_approval")
        access = self.authority.access_decision(
            workspace_id, person_id=approved_by_person_id, capability="finance.approve_posting",
            department_id=draft.get("department_id"),
        )
        if not access.get("allowed"):
            raise PermissionError(access.get("reason") or "finance_posting_approval_not_authorised")
        if approved_draft_hash != draft.get("draft_hash"):
            raise ValueError("approved_bookkeeping_draft_hash_mismatch")
        draft["posting_approval"] = {
            "approved_by_person_id": approved_by_person_id, "approved_at": _now(),
            "approved_draft_hash": approved_draft_hash, "authority_decision": access,
        }
        draft["status"] = "approved_for_internal_posting"
        draft.pop("draft_hash", None); draft["draft_hash"] = canonical_contract_hash(draft)
        self._save_draft(workspace_id, draft)
        return draft

    def post_internal(self, workspace_id: str, draft_id: str, *, posted_by_person_id: str) -> dict[str, Any]:
        draft = self.load(workspace_id, draft_id)
        if draft.get("status") == "posted_internal":
            return draft
        approval = draft.get("posting_approval") or {}
        if draft.get("status") != "approved_for_internal_posting" or not approval:
            raise PermissionError("exact_bookkeeping_posting_approval_required")
        access = self.authority.access_decision(
            workspace_id, person_id=posted_by_person_id, capability="finance.prepare",
            department_id=draft.get("department_id"),
        )
        if not access.get("allowed"):
            raise PermissionError(access.get("reason") or "finance_internal_posting_not_authorised")
        entry = {
            "entry_id": f"entry-{_safe(draft_id)}", "draft_id": draft_id,
            "workspace_id": workspace_id, "journal_date": draft.get("journal_date"),
            "currency": draft.get("currency"), "description": draft.get("description"),
            "lines": draft.get("lines"), "debit_total": draft.get("debit_total"),
            "credit_total": draft.get("credit_total"), "source_document_id": draft.get("source_document_id"),
            "approved_draft_hash": approval.get("approved_draft_hash"),
            "posted_by_person_id": posted_by_person_id, "posted_at": _now(),
            "external_write_performed": False,
        }
        entry["entry_hash"] = canonical_contract_hash(entry)
        ledger_path = self._dir(workspace_id) / "internal_journal.jsonl"
        existing = []
        if ledger_path.exists():
            existing = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not any(row.get("source_document_id") == entry["source_document_id"] for row in existing):
            with ledger_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, sort_keys=True) + "\n")
        draft["status"] = "posted_internal"
        draft["internal_posting"] = {key: entry[key] for key in ("entry_id", "entry_hash", "posted_at", "posted_by_person_id")}
        draft.pop("draft_hash", None); draft["draft_hash"] = canonical_contract_hash(draft)
        self._save_draft(workspace_id, draft)
        self._project(workspace_id, draft, entry, ledger_path)
        return draft

    def load(self, workspace_id: str, draft_id: str) -> dict[str, Any]:
        path = self._dir(workspace_id) / "drafts" / f"{_safe(draft_id)}.json"
        if not path.exists():
            raise FileNotFoundError(f"Bookkeeping draft not found: {draft_id}")
        value = json.loads(path.read_text(encoding="utf-8"))
        expected = value.get("draft_hash"); payload = dict(value); payload.pop("draft_hash", None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError("bookkeeping_draft_hash_mismatch")
        if value.get("workspace_id") != workspace_id:
            raise PermissionError("bookkeeping_workspace_isolation_violation")
        return value

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load(workspace_id, path.stem) for path in sorted(
            (self._dir(workspace_id) / "drafts").glob("*.json"),
            key=lambda item: item.stat().st_mtime, reverse=True,
        )]

    def ledger_summary(self, workspace_id: str) -> dict[str, Any]:
        """Return verified internal movements without mixing them into provider actuals."""
        path = self._dir(workspace_id) / "internal_journal.jsonl"
        entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
        accounts: dict[tuple[str, str, str], dict[str, Any]] = {}
        currencies: set[str] = set()
        total_debits = total_credits = 0.0
        for entry in entries:
            expected = entry.get("entry_hash")
            payload = dict(entry); payload.pop("entry_hash", None)
            if not expected or canonical_contract_hash(payload) != expected:
                raise ValueError(f"bookkeeping_entry_hash_mismatch:{entry.get('entry_id')}")
            if entry.get("workspace_id") != workspace_id:
                raise PermissionError("bookkeeping_workspace_isolation_violation")
            currencies.add(str(entry.get("currency") or "EUR"))
            entry_debits = round(sum(_money(line.get("debit")) for line in entry.get("lines") or []), 2)
            entry_credits = round(sum(_money(line.get("credit")) for line in entry.get("lines") or []), 2)
            if entry_debits != entry_credits:
                raise ValueError(f"bookkeeping_entry_unbalanced:{entry.get('entry_id')}")
            total_debits = round(total_debits + entry_debits, 2)
            total_credits = round(total_credits + entry_credits, 2)
            for line in entry.get("lines") or []:
                key = (str(line.get("account_code") or ""), str(line.get("account_name") or ""),
                       str(line.get("account_type") or "unclassified"))
                row = accounts.setdefault(key, {
                    "account_code": key[0], "account_name": key[1], "account_type": key[2],
                    "debit": 0.0, "credit": 0.0, "balance": 0.0,
                })
                row["debit"] = round(row["debit"] + _money(line.get("debit")), 2)
                row["credit"] = round(row["credit"] + _money(line.get("credit")), 2)
                row["balance"] = round(row["debit"] - row["credit"], 2)
        drafts = self.list(workspace_id)
        synced_entry_ids = {str((draft.get("internal_posting") or {}).get("entry_id")) for draft in drafts
                            if draft.get("status") == "synced_to_xero"}
        exported_count = sum(str(entry.get("entry_id")) in synced_entry_ids for entry in entries)
        sync_status = "fully_exported" if entries and exported_count == len(entries) else "partially_exported" if exported_count else "not_exported"
        return {
            "schema_version": "aion.finance.internal_ledger_summary.v1", "workspace_id": workspace_id,
            "entry_count": len(entries), "currencies": sorted(currencies),
            "total_debits": total_debits, "total_credits": total_credits,
            "balanced": total_debits == total_credits,
            "accounts": sorted(accounts.values(), key=lambda row: row["account_code"]),
            "provider_sync_status": sync_status, "provider_verified_entry_count": exported_count,
            "provider_pending_entry_count": max(0, len(entries) - exported_count),
            "included_in_provider_actuals": False,
            "boundary": "Internal postings remain a separate controlled movement layer until a provider confirms import; management reports must not add them to provider actuals twice.",
        }

    @staticmethod
    def _instruction_hash(value: dict[str, Any]) -> str:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _line(account_code: str, side: str, amount: float, label: str,
              *, tax_code: str | None = None, account_type: str) -> dict[str, Any]:
        return {"account_code": account_code, "account_name": label,
                "debit": amount if side == "debit" else 0.0,
                "credit": amount if side == "credit" else 0.0, "tax_code": tax_code,
                "account_type": account_type}

    @staticmethod
    def _control_label(code: str) -> str:
        return code.replace("control.", "").replace("_", " ").title()

    def _dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/bookkeeping"
        (path / "drafts").mkdir(parents=True, exist_ok=True)
        return path

    def _save_draft(self, workspace_id: str, draft: dict[str, Any]) -> None:
        path = self._dir(workspace_id) / "drafts" / f"{_safe(draft['draft_id'])}.json"
        path.write_text(json.dumps(draft, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _project(self, workspace_id: str, draft: dict[str, Any], entry: dict[str, Any], path: Path) -> None:
        summary = {
            "latest_entry_id": entry["entry_id"], "latest_entry_hash": entry["entry_hash"],
            "latest_posted_at": entry["posted_at"], "draft_id": draft["draft_id"],
            "source_document_id": draft["source_document_id"], "debit_total": draft["debit_total"],
            "credit_total": draft["credit_total"], "external_write_performed": False,
        }
        ledger_summary = self.ledger_summary(workspace_id)
        summary["internal_ledger"] = {
            "entry_count": ledger_summary["entry_count"], "balanced": ledger_summary["balanced"],
            "total_debits": ledger_summary["total_debits"], "total_credits": ledger_summary["total_credits"],
            "provider_sync_status": ledger_summary["provider_sync_status"],
            "included_in_provider_actuals": False,
        }
        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            intelligence.setdefault("departments", {}).setdefault("finance", {})["latest_bookkeeping_entry"] = summary
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1
            self.repository.save_dict(workspace_id, "department_intelligence", intelligence)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom:
            boardroom.setdefault("boardroom", {}).setdefault("runtime", {})["latest_finance_bookkeeping_entry"] = summary
            self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)
        tree = WorkflowFileCabinetRepository.load(workspace_id)
        folders = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        finance = next((item for item in folders if item.get("id") == "folder_finance"), None)
        if finance is None:
            finance = {"id": "folder_finance", "name": "Finance", "type": "department", "children": []}; folders.append(finance)
        children = finance.setdefault("children", [])
        journal = next((item for item in children if item.get("id") == "folder_finance_bookkeeping"), None)
        if journal is None:
            journal = {"id": "folder_finance_bookkeeping", "name": "Bookkeeping Journal", "type": "folder", "children": []}; children.append(journal)
        journal.setdefault("children", []).append({
            "id": f"finance_bookkeeping_{entry['entry_id']}", "name": entry["entry_id"],
            "type": "business_container_artifact", "document_type": "finance_bookkeeping_entry",
            "status": "posted_internal", "target": {"storage_path": str(path), "entry_hash": entry["entry_hash"]},
        })
        tree["folders"] = folders
        tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}
        WorkflowFileCabinetRepository.save(workspace_id, tree)
