"""Transaction-level Finance matching and human review.

Suggestions are local drafts. Accepting a suggestion records review intent only;
it never marks an item reconciled in Xero or another accounting provider.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.business_container_repository_factory import configured_business_container_repository
from backend.modules.aion_business.runtime.business_vault_runtime import configured_business_vault_runtime, guardian_mode_requested
from backend.modules.aion_business.runtime.finance_ledger_service import FinanceLedgerService
from backend.modules.aion_business.runtime.finance_operations_store import FinanceOperationsStore
from backend.modules.aion_business.runtime.finance_counterparty_intelligence_service import (
    FinanceCounterpartyIntelligenceService,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _days_between(left: Any, right: Any) -> int | None:
    try:
        return abs((date.fromisoformat(str(left)[:10]) - date.fromisoformat(str(right)[:10])).days)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


class FinanceTransactionReconciliationService:
    DECISIONS = {"accept_match", "reject_match", "needs_investigation"}

    def __init__(self, repository: BusinessContainerRepository | None = None,
                 ledger_service: FinanceLedgerService | None = None,
                 counterparty_intelligence: FinanceCounterpartyIntelligenceService | None = None, *,
                 domain_store: VaultDomainStore | None = None,
                 operations_store: FinanceOperationsStore | None = None) -> None:
        self.repository = repository or configured_business_container_repository()
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(runtime.guardian, actor_id="finance-reconciliation-runtime")
        self.operations_store = operations_store or FinanceOperationsStore(
            domain_store=self.domain_store,
        )
        self.ledger_service = ledger_service or FinanceLedgerService(
            self.repository, domain_store=self.domain_store,
            operations_store=self.operations_store,
        )
        self.counterparty_intelligence = counterparty_intelligence or FinanceCounterpartyIntelligenceService(
            domain_store=self.domain_store, operations_store=self.operations_store,
        )

    def run(self, workspace_id: str, *, created_by: str = "finance_pilot",
            created_at: str | None = None, amount_tolerance: float = 0.01,
            date_window_days: int = 7, classify_unmatched: bool = True,
            classification_limit: int = 25,
            preferred_provider: str | None = None, preferred_model: str | None = None) -> dict[str, Any]:
        ledger = self.ledger_service.latest(workspace_id, include_records=True)
        if not ledger:
            raise FileNotFoundError("Build the canonical Finance ledger before matching transactions.")
        records = ledger.get("records") or {}
        invoices = records.get("invoices") or []
        payments = records.get("payments") or []
        bank = records.get("bank_transactions") or []
        matches: list[dict[str, Any]] = []
        matched_payment_ids: set[str] = set()
        matched_invoice_ids: set[str] = set()
        matched_bank_ids: set[str] = set()
        classifications: list[dict[str, Any]] = []

        for payment in payments:
            candidates = []
            for invoice in invoices:
                score, reasons = self._payment_score(payment, invoice, amount_tolerance, date_window_days)
                if score:
                    candidates.append((score, reasons, invoice))
            if not candidates:
                continue
            score, reasons, invoice = sorted(candidates, key=lambda item: item[0], reverse=True)[0]
            confidence = "high" if score >= 90 else "medium" if score >= 65 else "low"
            match_id = f"match-payment-{_safe(payment.get('payment_id'))}-{_safe(invoice.get('invoice_id'))}"
            matches.append({"match_id": match_id, "match_type": "payment_to_invoice", "confidence_score": score,
                            "confidence": confidence, "reasons": reasons, "payment": self._payment_view(payment),
                            "invoice": self._invoice_view(invoice), "review": None, "provider_write_status": "not_requested"})
            if confidence in {"high", "medium"}:
                matched_payment_ids.add(str(payment.get("payment_id"))); matched_invoice_ids.add(str(invoice.get("invoice_id")))

        for transaction in bank:
            if transaction.get("is_reconciled"):
                continue
            candidates = []
            for invoice in invoices:
                score, reasons = self._bank_score(transaction, invoice, amount_tolerance, date_window_days)
                if score:
                    candidates.append((score, reasons, invoice))
            if not candidates:
                continue
            score, reasons, invoice = sorted(candidates, key=lambda item: item[0], reverse=True)[0]
            confidence = "high" if score >= 90 else "medium" if score >= 65 else "low"
            match_id = f"match-bank-{_safe(transaction.get('bank_transaction_id'))}-{_safe(invoice.get('invoice_id'))}"
            matches.append({"match_id": match_id, "match_type": "bank_transaction_to_invoice", "confidence_score": score,
                            "confidence": confidence, "reasons": reasons, "bank_transaction": self._bank_view(transaction),
                            "invoice": self._invoice_view(invoice), "review": None, "provider_write_status": "not_requested"})
            if confidence in {"high", "medium"}:
                matched_bank_ids.add(str(transaction.get("bank_transaction_id"))); matched_invoice_ids.add(str(invoice.get("invoice_id")))

        duplicates = self._duplicates(bank, payments)
        exceptions: list[dict[str, Any]] = []
        for invoice in invoices:
            if invoice.get("amount_due", 0) > 0 and invoice.get("is_overdue"):
                exceptions.append(self._exception("overdue_invoice" if invoice.get("invoice_type") == "sales_invoice" else "overdue_supplier_bill",
                                                  "high", invoice.get("invoice_id"), self._invoice_view(invoice)))
        for payment in payments:
            if str(payment.get("payment_id")) not in matched_payment_ids:
                exceptions.append(self._exception("unmatched_payment", "medium", payment.get("payment_id"), self._payment_view(payment)))
        for transaction in bank:
            if not transaction.get("is_reconciled") and str(transaction.get("bank_transaction_id")) not in matched_bank_ids:
                classification = None
                if classify_unmatched and len(classifications) < max(0, min(classification_limit, 50)):
                    classification = self.counterparty_intelligence.classify(
                        workspace_id, transaction, records.get("accounts") or [],
                        preferred_provider=preferred_provider, preferred_model=preferred_model,
                    )
                    classifications.append(classification)
                detail = self._bank_view(transaction)
                if classification:
                    detail["classification_suggestion_id"] = classification.get("suggestion_id")
                    detail["classification_status"] = classification.get("status")
                exceptions.append(self._exception("unmatched_bank_transaction", "medium", transaction.get("bank_transaction_id"), detail))
        exceptions.extend(duplicates)

        occurred_at = created_at or _now()
        run_id = f"transaction-reconciliation-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
        record = {
            "schema_version": "aion.finance.transaction_reconciliation.v1",
            "run_id": run_id, "workspace_id": workspace_id, "ledger_id": ledger["ledger_id"],
            "ledger_hash": ledger["ledger_hash"], "created_at": occurred_at, "created_by": created_by,
            "status": "review_required" if matches or exceptions else "no_items",
            "policy": {"amount_tolerance": amount_tolerance, "date_window_days": date_window_days,
                       "classification_limit": max(0, min(classification_limit, 50)),
                       "accepted_match_does_not_post_to_provider": True},
            "match_count": len(matches), "exception_count": len(exceptions),
            "confidence_counts": {level: sum(item["confidence"] == level for item in matches) for level in ("high", "medium", "low")},
            "matches": matches, "exceptions": exceptions, "classifications": classifications,
            "classification_count": len(classifications),
            "external_write_performed": False, "provider_reconciliations_posted": 0,
        }
        record["run_hash"] = canonical_contract_hash(record)
        path = self._dir(workspace_id) / f"{run_id}.json"
        self._write(path, record)
        self._index(workspace_id, record, path); self._project(workspace_id, record, path)
        return record

    def review_classification(self, workspace_id: str, run_id: str, suggestion_id: str, *, decision: str,
                              reviewed_by: str, selected_account: dict[str, Any] | None = None,
                              notes: str | None = None, reviewed_at: str | None = None) -> dict[str, Any]:
        path = self._dir(workspace_id) / f"{_safe(run_id)}.json"
        if not self._exists(path):
            raise FileNotFoundError(f"Transaction reconciliation not found: {run_id}")
        record = self._read(path); self._verify(record)
        suggestion = next((item for item in record.get("classifications") or [] if item.get("suggestion_id") == suggestion_id), None)
        if suggestion is None:
            raise FileNotFoundError(f"Counterparty suggestion not found: {suggestion_id}")
        review = self.counterparty_intelligence.confirm(
            workspace_id, suggestion, decision=decision, reviewed_by=reviewed_by,
            selected_account=selected_account, notes=notes, reviewed_at=reviewed_at or _now(),
        )
        suggestion["review"] = review
        suggestion["status"] = "mapping_confirmed" if decision == "accept_mapping" else "rejected" if decision == "reject_mapping" else "needs_clarification"
        suggestion.pop("suggestion_hash", None); suggestion["suggestion_hash"] = canonical_contract_hash(suggestion)
        record["reviewed_classification_count"] = sum(bool(item.get("review")) for item in record.get("classifications") or [])
        record.pop("run_hash", None); record["run_hash"] = canonical_contract_hash(record)
        self._write(path, record)
        self._project(workspace_id, record, path)
        return record

    def review(self, workspace_id: str, run_id: str, match_id: str, *, decision: str,
               reviewed_by: str, notes: str | None = None, reviewed_at: str | None = None) -> dict[str, Any]:
        if decision not in self.DECISIONS:
            raise ValueError("invalid_transaction_match_decision")
        path = self._dir(workspace_id) / f"{_safe(run_id)}.json"
        if not self._exists(path):
            raise FileNotFoundError(f"Transaction reconciliation not found: {run_id}")
        record = self._read(path); self._verify(record)
        match = next((item for item in record.get("matches") or [] if item.get("match_id") == match_id), None)
        if match is None:
            raise FileNotFoundError(f"Transaction match not found: {match_id}")
        match["review"] = {"decision": decision, "reviewed_by": reviewed_by, "reviewed_at": reviewed_at or _now(), "notes": notes}
        match["provider_write_status"] = "approved_draft_not_posted" if decision == "accept_match" else "not_requested"
        record["reviewed_match_count"] = sum(bool(item.get("review")) for item in record.get("matches") or [])
        record["accepted_draft_match_count"] = sum((item.get("review") or {}).get("decision") == "accept_match" for item in record.get("matches") or [])
        record["status"] = "reviewed_drafts_not_posted" if record["reviewed_match_count"] == record["match_count"] else "review_required"
        record["external_write_performed"] = False; record["provider_reconciliations_posted"] = 0
        record.pop("run_hash", None); record["run_hash"] = canonical_contract_hash(record)
        self._write(path, record)
        self._project(workspace_id, record, path)
        return record

    def latest(self, workspace_id: str) -> dict[str, Any] | None:
        if self.domain_store is not None:
            rows = self.domain_store.list("finance.reconciliation_records", workspace_id=workspace_id)
            rows.sort(key=lambda row: str((row.get("payload") or {}).get("created_at") or ""), reverse=True)
            if not rows: return None
            record = dict(rows[0]["payload"]); self._verify(record); return record
        paths = sorted(self._dir(workspace_id).glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not paths:
            return None
        record = json.loads(paths[0].read_text(encoding="utf-8")); self._verify(record); return record

    def _dir(self, workspace_id: str, *, create: bool = False) -> Path:
        if self.domain_store is not None:
            return Path("/__tessaris_guardian_finance_reconciliation__") / _safe(workspace_id) / "finance" / "transaction_reconciliations"
        path = (
            AIONBusinessPaths.BUSINESS_CONTAINERS
            / _safe(workspace_id)
            / "finance/transaction_reconciliations"
        )
        if create:
            AIONBusinessPaths.ensure_base_dirs()
            path.mkdir(parents=True, exist_ok=True)
        return path

    def _identity(self, path: Path) -> tuple[str, str]:
        parts = path.parts
        marker = parts.index("__tessaris_guardian_finance_reconciliation__")
        workspace_id = parts[marker + 1]
        reconciliations = parts.index("transaction_reconciliations", marker + 2)
        return workspace_id, Path(*parts[reconciliations + 1:]).with_suffix("").as_posix()

    def _exists(self, path: Path) -> bool:
        if self.domain_store is None: return path.exists()
        workspace_id, entity_id = self._identity(path)
        return self.domain_store.get_optional("finance.reconciliation_records", workspace_id=workspace_id, entity_id=entity_id) is not None

    def _read(self, path: Path) -> dict[str, Any]:
        if self.domain_store is None: return json.loads(path.read_text(encoding="utf-8"))
        workspace_id, entity_id = self._identity(path)
        return dict(self.domain_store.get("finance.reconciliation_records", workspace_id=workspace_id, entity_id=entity_id)["payload"])

    def _write(self, path: Path, record: dict[str, Any]) -> None:
        if self.domain_store is not None:
            workspace_id, entity_id = self._identity(path)
            current = self.domain_store.get_optional("finance.reconciliation_records", workspace_id=workspace_id, entity_id=entity_id)
            self.domain_store.put(
                "finance.reconciliation_records", workspace_id=workspace_id, entity_id=entity_id,
                payload=record, expected_version=int(current["version"]) if current else None,
                actor_id="finance-reconciliation-runtime",
            )
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _payment_score(payment: dict[str, Any], invoice: dict[str, Any], tolerance: float, window: int) -> tuple[int, list[str]]:
        score = 0; reasons = []
        if payment.get("invoice_id") and payment.get("invoice_id") == invoice.get("invoice_id"):
            score += 80; reasons.append("Xero payment carries the invoice ID")
        if payment.get("invoice_number") and payment.get("invoice_number") == invoice.get("invoice_number"):
            score += 15; reasons.append("invoice number matches")
        amount_target = invoice.get("amount_paid") or invoice.get("total")
        if abs(float(payment.get("amount") or 0) - float(amount_target or 0)) <= max(tolerance, abs(float(amount_target or 0)) * tolerance):
            score += 10; reasons.append("amount matches")
        days = _days_between(payment.get("date"), invoice.get("date"))
        if days is not None and days <= window:
            score += 5; reasons.append(f"dates are within {window} days")
        return min(score, 100), reasons

    @staticmethod
    def _bank_score(transaction: dict[str, Any], invoice: dict[str, Any], tolerance: float, window: int) -> tuple[int, list[str]]:
        score = 0; reasons = []
        amount = abs(float(transaction.get("total") or 0)); targets = [abs(float(invoice.get(key) or 0)) for key in ("total", "amount_due", "amount_paid")]
        if any(abs(amount - target) <= max(tolerance, target * tolerance) for target in targets if target):
            score += 55; reasons.append("amount matches invoice total, paid or due amount")
        reference = _text(transaction.get("reference")); invoice_refs = {_text(invoice.get("invoice_number")), _text(invoice.get("reference"))}
        if reference and any(value and (value in reference or reference in value) for value in invoice_refs):
            score += 30; reasons.append("reference contains invoice number or reference")
        transaction_contact = _text((transaction.get("contact") or {}).get("display_name")); invoice_contact = _text((invoice.get("contact") or {}).get("display_name"))
        if transaction_contact and transaction_contact == invoice_contact:
            score += 15; reasons.append("counterparty matches")
        days = _days_between(transaction.get("date"), invoice.get("date"))
        if days is not None and days <= window:
            score += 10; reasons.append(f"dates are within {window} days")
        return min(score, 100), reasons

    @staticmethod
    def _duplicates(bank: list[dict[str, Any]], payments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for collection_name, records, id_key, amount_key in (("bank_transaction", bank, "bank_transaction_id", "total"), ("payment", payments, "payment_id", "amount")):
            seen: dict[tuple[Any, ...], str] = {}
            for item in records:
                fingerprint = (round(abs(float(item.get(amount_key) or 0)), 2), item.get("date"), _text(item.get("reference")))
                if fingerprint in seen and fingerprint[0]:
                    result.append(FinanceTransactionReconciliationService._exception("possible_duplicate", "high", item.get(id_key),
                        {"collection": collection_name, "record_id": item.get(id_key), "possible_duplicate_of": seen[fingerprint], "amount": fingerprint[0], "date": fingerprint[1], "reference": item.get("reference")}))
                else:
                    seen[fingerprint] = str(item.get(id_key))
        return result

    @staticmethod
    def _exception(kind: str, severity: str, provider_id: Any, detail: dict[str, Any]) -> dict[str, Any]:
        return {"exception_id": f"exception-{_safe(kind)}-{_safe(provider_id)}", "kind": kind, "severity": severity,
                "detail": detail, "status": "open", "provider_write_status": "not_requested"}

    @staticmethod
    def _invoice_view(item: dict[str, Any]) -> dict[str, Any]:
        return {key: item.get(key) for key in ("invoice_id", "invoice_number", "invoice_type", "status", "contact", "date", "due_date", "total", "amount_paid", "amount_due", "reference", "is_overdue")}

    @staticmethod
    def _payment_view(item: dict[str, Any]) -> dict[str, Any]:
        return {key: item.get(key) for key in ("payment_id", "date", "amount", "status", "reference", "invoice_id", "invoice_number", "account_id")}

    @staticmethod
    def _bank_view(item: dict[str, Any]) -> dict[str, Any]:
        return {key: item.get(key) for key in ("bank_transaction_id", "transaction_type", "status", "contact", "date", "reference", "total", "bank_account_id", "is_reconciled")}

    def _index(self, workspace_id: str, record: dict[str, Any], path: Path) -> None:
        tree = WorkflowFileCabinetRepository.load(workspace_id); folders = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        finance = next((item for item in folders if item.get("id") == "folder_finance"), None)
        if finance is None:
            finance = {"id": "folder_finance", "name": "Finance", "type": "department", "children": []}; folders.append(finance)
        children = finance.setdefault("children", []); folder = next((item for item in children if item.get("id") == "folder_finance_transaction_reconciliations"), None)
        if folder is None:
            folder = {"id": "folder_finance_transaction_reconciliations", "name": "Transaction Reconciliation", "type": "folder", "children": []}; children.append(folder)
        target = ({"vault_domain_id": "finance.reconciliation_records", "vault_entity_id": self._identity(path)[1], "run_hash": record["run_hash"]}
                  if self.domain_store is not None else {"storage_path": str(path), "run_hash": record["run_hash"]})
        folder.setdefault("children", []).append({"id": f"finance_transaction_reconciliation_{record['run_id']}", "name": record["run_id"], "type": "business_container_artifact",
            "document_type": "finance_transaction_reconciliation", "status": record["status"], "target": target})
        tree["folders"] = folders; tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}; WorkflowFileCabinetRepository.save(workspace_id, tree)

    def _project(self, workspace_id: str, record: dict[str, Any], path: Path) -> None:
        summary = {key: record.get(key) for key in ("run_id", "ledger_id", "created_at", "status", "match_count", "exception_count", "confidence_counts", "classification_count", "reviewed_classification_count", "reviewed_match_count", "accepted_draft_match_count", "run_hash")}
        if self.domain_store is not None:
            summary["vault_domain_id"] = "finance.reconciliation_records"
            summary["vault_entity_id"] = self._identity(path)[1]
        else:
            summary["storage_path"] = str(path)
        summary["external_write_performed"] = False
        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            finance = intelligence.setdefault("departments", {}).setdefault("finance", {}); finance["latest_transaction_reconciliation"] = summary
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1; self.repository.save_dict(workspace_id, "department_intelligence", intelligence)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom:
            boardroom.setdefault("boardroom", {}).setdefault("runtime", {})["latest_finance_transaction_reconciliation"] = summary
            self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)

    @staticmethod
    def _verify(record: dict[str, Any]) -> None:
        expected = record.get("run_hash"); payload = dict(record); payload.pop("run_hash", None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError("finance_transaction_reconciliation_hash_mismatch")
