"""Evidence-backed month-end readiness without pretending to file or close."""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
from pathlib import Path
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_bookkeeping_service import FinanceBookkeepingService
from backend.modules.aion_business.runtime.finance_ledger_service import FinanceLedgerService
from backend.modules.aion_business.runtime.finance_sales_service import FinanceSalesService
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class FinanceMonthEndService:
    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = OrganizationAuthorityService(self.repository)
        self.bookkeeping = FinanceBookkeepingService(self.repository, self.authority)
        self.sales = FinanceSalesService(self.repository, self.authority, self.bookkeeping)
        self.ledger = FinanceLedgerService(self.repository)

    def evaluate(self, workspace_id: str, *, period_end: str,
                 prepared_by_person_id: str) -> dict[str, Any]:
        decision = self.authority.access_decision(
            workspace_id, person_id=prepared_by_person_id, capability="finance.prepare")
        if not decision.get("allowed"):
            raise PermissionError(decision.get("reason") or "finance_prepare_not_authorised")
        period = date.fromisoformat(str(period_end)[:10])
        inbox = self.repository.load_optional_dict(workspace_id, "finance_inbox") or {}
        documents = inbox.get("documents") or []
        pending_documents = [row for row in documents if row.get("status") in {
            "needs_submitter", "needs_review", "needs_information", "awaiting_approval", "approved_for_accounting"}]
        drafts = self.bookkeeping.list(workspace_id)
        pending_mapping = [row for row in drafts if row.get("unresolved_controls")]
        pending_export = [row for row in drafts if row.get("status") in {"posted_internal", "approved_for_internal_posting"}]
        ledger = self.ledger.latest(workspace_id) or {}
        counts = ledger.get("record_counts") or {}
        summaries = ledger.get("summaries") or {}
        financial = self.repository.load_optional_dict(workspace_id, "business_financial_model") or {}
        xero = (financial.get("integration_evidence") or {}).get("xero") or {}
        evidence = xero.get("evidence_ref") or {}
        report_names = set((xero.get("sync_summary") or {}).get("reports_received") or [])
        if not report_names:
            connection_path = AIONBusinessPaths.business_container_dir(workspace_id) / "integrations/xero/connection.json"
            if connection_path.exists():
                connection = json.loads(connection_path.read_text(encoding="utf-8"))
                report_names = set((connection.get("sync_summary") or {}).get("reports_received") or [])
        checks = [
            self._check("provider_sync", bool(evidence.get("sync_id")), "block",
                        "A completed provider sync is available." if evidence.get("sync_id") else "Synchronise the accounting provider."),
            self._check("profit_and_loss", "profit_and_loss" in report_names, "block", "Profit and Loss report received."),
            self._check("balance_sheet", "balance_sheet" in report_names, "block", "Balance Sheet report received."),
            self._check("finance_inbox_clear", not pending_documents, "warn",
                        f"{len(pending_documents)} Finance Inbox item(s) still need review or posting."),
            self._check("account_mapping_complete", not pending_mapping, "block",
                        f"{len(pending_mapping)} bookkeeping draft(s) have unresolved account or tax mappings."),
            self._check("internal_exports_complete", not pending_export, "warn",
                        f"{len(pending_export)} approved internal entry or entries are not provider-verified."),
            self._check("bank_evidence_available", int(ledger.get("provider_bank_transaction_count")
                                                        if ledger.get("provider_bank_transaction_count") is not None
                                                        else counts.get("bank_transactions") or 0) > 0, "warn",
                        f"{int(ledger.get('provider_bank_transaction_count') if ledger.get('provider_bank_transaction_count') is not None else counts.get('bank_transactions') or 0)} provider-visible bank transaction(s); controlled fixtures do not satisfy this check."),
            self._check("payment_evidence_available", int(counts.get("payments") or 0) > 0, "warn",
                        f"{int(counts.get('payments') or 0)} provider-visible payment(s)."),
            self._check("overdue_receivables_reviewed", float(summaries.get("overdue_receivables") or 0) == 0, "warn",
                        f"Overdue receivables: {float(summaries.get('overdue_receivables') or 0):.2f}."),
            self._check("sales_drafts_reviewed", self.sales.summary(workspace_id)["draft_count"] == 0, "warn",
                        f"{self.sales.summary(workspace_id)['draft_count']} local sales invoice draft(s) remain."),
        ]
        blockers = [row for row in checks if row["status"] == "block"]
        warnings = [row for row in checks if row["status"] == "warn"]
        record = {
            "schema_version": "aion.finance.month_end_readiness.v1",
            "month_end_id": f"month-end-{period.isoformat()}", "workspace_id": workspace_id,
            "period_end": period.isoformat(), "prepared_at": _now(),
            "prepared_by_person_id": prepared_by_person_id, "authority_decision": decision,
            "status": "blocked" if blockers else "ready_for_human_review",
            "checks": checks, "blocker_count": len(blockers), "warning_count": len(warnings),
            "provider_source": {"sync_id": evidence.get("sync_id"), "snapshot_hash": evidence.get("snapshot_hash")},
            "financial_snapshot": {"accounts_receivable": summaries.get("accounts_receivable"),
                                   "accounts_payable": summaries.get("accounts_payable"),
                                   "overdue_receivables": summaries.get("overdue_receivables"),
                                   "overdue_payables": summaries.get("overdue_payables")},
            "external_write_performed": False, "period_closed": False,
            "boundary": "Readiness is evidence-backed but does not close a provider period, file tax, or approve adjustments.",
        }
        record["readiness_hash"] = canonical_contract_hash(record)
        path = self._path(workspace_id, period.isoformat()); path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._project(workspace_id, record, path)
        return record

    def latest(self, workspace_id: str) -> dict[str, Any] | None:
        paths = sorted(self._dir(workspace_id).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not paths: return None
        record = json.loads(paths[0].read_text(encoding="utf-8")); expected = record.get("readiness_hash")
        payload = dict(record); payload.pop("readiness_hash", None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError("finance_month_end_readiness_hash_mismatch")
        return record

    @staticmethod
    def _check(check_id: str, passed: bool, failure_level: str, detail: str) -> dict[str, Any]:
        return {"check_id": check_id, "status": "pass" if passed else failure_level,
                "passed": bool(passed), "detail": detail}

    def _project(self, workspace_id: str, record: dict[str, Any], path: Path) -> None:
        summary = {key: record[key] for key in (
            "month_end_id", "period_end", "status", "blocker_count", "warning_count", "readiness_hash")}
        summary["storage_path"] = str(path)
        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            intelligence.setdefault("departments", {}).setdefault("finance", {})["latest_month_end_readiness"] = summary
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1
            self.repository.save_dict(workspace_id, "department_intelligence", intelligence)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom:
            boardroom.setdefault("boardroom", {}).setdefault("runtime", {})["latest_finance_month_end_readiness"] = summary
            self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)

    def _dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/month_end"
        path.mkdir(parents=True, exist_ok=True); return path

    def _path(self, workspace_id: str, period_end: str) -> Path:
        return self._dir(workspace_id) / f"month-end-{period_end}.json"
