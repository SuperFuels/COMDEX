"""Provider-neutral, exact-approved bank activity evidence.

The service accepts reviewed imports and controlled test fixtures without
pretending they came from Xero or a live bank feed. Only exact-approved records
enter the canonical matching ledger. It never moves money or writes externally.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


class FinanceBankActivityService:
    SOURCES = {"bank_csv", "open_banking", "controlled_test_fixture"}

    def __init__(self, repository: BusinessContainerRepository | None = None,
                 authority: OrganizationAuthorityService | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = authority or OrganizationAuthorityService(self.repository)

    def prepare(self, workspace_id: str, *, source_type: str, transaction_type: str,
                transaction_date: str, amount: float, currency: str, reference: str,
                counterparty: str, bank_account_id: str | None,
                source_document_id: str | None, source_invoice_id: str | None,
                test_purpose: str | None, prepared_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, prepared_by_person_id, "finance.prepare")
        source_type = str(source_type or "").strip()
        if source_type not in self.SOURCES:
            raise ValueError("unsupported_bank_activity_source")
        if source_type == "controlled_test_fixture" and not str(test_purpose or "").strip():
            raise ValueError("controlled_bank_fixture_test_purpose_required")
        transaction_type = str(transaction_type or "").strip().lower()
        if transaction_type not in {"spend", "receive"}:
            raise ValueError("invalid_bank_activity_transaction_type")
        day = date.fromisoformat(str(transaction_date)[:10]).isoformat()
        value = round(abs(float(amount or 0)), 2)
        if value <= 0:
            raise ValueError("positive_bank_activity_amount_required")
        signed = -value if transaction_type == "spend" else value
        instruction = {
            "workspace_id": workspace_id, "source_type": source_type,
            "transaction_type": transaction_type, "date": day, "total": signed,
            "currency": str(currency or "EUR").upper(), "reference": str(reference or "").strip(),
            "counterparty": str(counterparty or "").strip(),
            "bank_account_id": str(bank_account_id or "").strip() or None,
            "source_document_id": str(source_document_id or "").strip() or None,
            "source_invoice_id": str(source_invoice_id or "").strip() or None,
            "test_purpose": str(test_purpose or "").strip() or None,
        }
        if not instruction["reference"] or not instruction["counterparty"]:
            raise ValueError("bank_activity_reference_and_counterparty_required")
        key = canonical_contract_hash(instruction).removeprefix("sha256:")[:20]
        record_id = f"bank-activity-{key}"
        path = self._path(workspace_id, record_id)
        if path.exists():
            return self.load(workspace_id, record_id)
        record = {
            "schema_version": "aion.finance.bank_activity.v1", "record_id": record_id,
            **instruction, "status": "exact_evidence_approval_required",
            "prepared_at": _now(), "prepared_by_person_id": prepared_by_person_id,
            "approval": None, "external_write_performed": False,
            "provider_reconciliation_posted": False,
            "truth_boundary": (
                "Controlled test evidence; not a provider-sourced or real bank transaction."
                if source_type == "controlled_test_fixture" else
                "Owner-approved imported bank evidence; not provider-verified until an adapter confirms it."
            ),
        }
        self._save(workspace_id, record)
        return record

    def approve(self, workspace_id: str, record_id: str, *, approved_by_person_id: str,
                approved_record_hash: str) -> dict[str, Any]:
        record = self.load(workspace_id, record_id)
        if record.get("status") == "approved_for_matching":
            return record
        decision = self._require(workspace_id, approved_by_person_id, "finance.approve_posting")
        if approved_record_hash != record.get("record_hash"):
            raise ValueError("approved_bank_activity_hash_mismatch")
        record["approval"] = {
            "approved_by_person_id": approved_by_person_id, "approved_at": _now(),
            "approved_record_hash": approved_record_hash, "authority_decision": decision,
        }
        record["status"] = "approved_for_matching"
        self._save(workspace_id, record)
        return record

    def ledger_records(self, workspace_id: str) -> list[dict[str, Any]]:
        result = []
        for record in self.list(workspace_id):
            if record.get("status") != "approved_for_matching":
                continue
            result.append({
                "bank_transaction_id": record["record_id"],
                "transaction_type": record["transaction_type"], "status": "APPROVED_EVIDENCE",
                "contact": {"contact_id": None, "display_name": record["counterparty"]},
                "date": record["date"], "reference": record["reference"],
                "currency": record["currency"], "subtotal": record["total"],
                "tax": 0.0, "total": record["total"], "line_items": [],
                "bank_account_id": record.get("bank_account_id"), "is_reconciled": False,
                "source_document_id": record.get("source_document_id"),
                "source_invoice_id": record.get("source_invoice_id"),
                "source_ref": {
                    "provider": None, "collection": "canonical_bank_activity",
                    "provider_id": None, "record_id": record["record_id"],
                    "source_type": record["source_type"],
                    "verification_status": (
                        "controlled_test_fixture" if record["source_type"] == "controlled_test_fixture"
                        else "owner_approved_import"
                    ),
                    "record_hash": record["record_hash"],
                },
            })
        return result

    def load(self, workspace_id: str, record_id: str) -> dict[str, Any]:
        path = self._path(workspace_id, record_id)
        if not path.exists():
            raise FileNotFoundError(record_id)
        record = json.loads(path.read_text(encoding="utf-8"))
        expected = record.get("record_hash"); payload = dict(record); payload.pop("record_hash", None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError("finance_bank_activity_hash_mismatch")
        if record.get("workspace_id") != workspace_id:
            raise PermissionError("finance_bank_activity_workspace_isolation_violation")
        return record

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load(workspace_id, path.stem) for path in sorted(
            self._dir(workspace_id).glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)]

    def _require(self, workspace_id: str, person_id: str, capability: str) -> dict[str, Any]:
        decision = self.authority.access_decision(workspace_id, person_id=person_id, capability=capability)
        if not decision.get("allowed"):
            raise PermissionError(decision.get("reason") or f"{capability}_not_authorised")
        return decision

    def _dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/bank_activity"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, workspace_id: str, record_id: str) -> Path:
        return self._dir(workspace_id) / f"{_safe(record_id)}.json"

    def _save(self, workspace_id: str, record: dict[str, Any]) -> None:
        record.pop("record_hash", None); record["record_hash"] = canonical_contract_hash(record)
        self._path(workspace_id, record["record_id"]).write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
