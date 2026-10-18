"""Exact-payload Xero reconciliation handoff.

Xero does not expose bank-statement reconciliation through its Accounting API.
This adapter therefore creates an inspectable, approved manual handoff and an
immutable blocked receipt instead of falsely reporting a provider write.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.business_vault_runtime import configured_business_vault_runtime, guardian_mode_requested
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


class XeroReconciliationHandoffService:
    """Proves approval and receipt behaviour while provider reconciliation is unsupported."""

    LIMITATION_CODE = "xero_bank_statement_reconciliation_api_not_supported"

    def __init__(self, *, domain_store: VaultDomainStore | None = None) -> None:
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(runtime.guardian, actor_id="xero-handoff-runtime")

    def prepare(self, workspace_id: str, reconciliation: dict[str, Any], match_id: str, *,
                prepared_by: str = "finance_pilot", prepared_at: str | None = None) -> dict[str, Any]:
        if reconciliation.get("workspace_id") != workspace_id:
            raise PermissionError("xero_reconciliation_handoff_business_isolation_violation")
        match = next((item for item in reconciliation.get("matches") or [] if item.get("match_id") == match_id), None)
        if not match:
            raise FileNotFoundError(f"Transaction match not found: {match_id}")
        if (match.get("review") or {}).get("decision") != "accept_match":
            raise PermissionError("accepted_transaction_match_required")
        payload = {
            "provider": "xero", "operation": "manual_bank_reconciliation_handoff",
            "workspace_id": workspace_id, "run_id": reconciliation.get("run_id"),
            "ledger_id": reconciliation.get("ledger_id"), "match_id": match_id,
            "match_type": match.get("match_type"), "payment": match.get("payment"),
            "bank_transaction": match.get("bank_transaction"), "invoice": match.get("invoice"),
            "provider_limitation": self.LIMITATION_CODE,
        }
        handoff_id = f"xero-handoff-{_safe(match_id)}"
        record = {"schema_version": "aion.xero.reconciliation_handoff.v1", "handoff_id": handoff_id,
                  "workspace_id": workspace_id, "prepared_at": prepared_at or _now(), "prepared_by": prepared_by,
                  "payload": payload, "payload_hash": canonical_contract_hash(payload),
                  "approval": None, "status": "exact_approval_required", "external_write_performed": False}
        record["handoff_hash"] = canonical_contract_hash(record)
        self._save(workspace_id, record); return record

    def decide(self, workspace_id: str, handoff_id: str, *, approved: bool, decided_by: str,
               decided_payload_hash: str | None, reason: str | None = None,
               decided_at: str | None = None) -> dict[str, Any]:
        record = self.load(workspace_id, handoff_id)
        if record.get("approval"):
            raise ValueError("xero_reconciliation_handoff_already_decided")
        if approved and decided_payload_hash != record.get("payload_hash"):
            raise ValueError("approved_payload_hash_mismatch")
        record["approval"] = {"status": "approved" if approved else "rejected", "decided_by": decided_by,
                              "decided_at": decided_at or _now(), "decided_payload_hash": decided_payload_hash if approved else None,
                              "reason": reason}
        record["status"] = "approved_manual_handoff" if approved else "rejected"
        record.pop("handoff_hash", None); record["handoff_hash"] = canonical_contract_hash(record)
        self._save(workspace_id, record); return record

    def execute(self, workspace_id: str, handoff_id: str, *, attempted_by: str,
                attempted_at: str | None = None) -> dict[str, Any]:
        record = self.load(workspace_id, handoff_id)
        approval = record.get("approval") or {}
        if approval.get("status") != "approved" or approval.get("decided_payload_hash") != record.get("payload_hash"):
            raise PermissionError("exact_payload_approval_required")
        receipt_entity_id = f"xero_handoffs/{_safe(handoff_id)}/blocked_receipt"
        receipt_path = self._dir(workspace_id) / f"{_safe(handoff_id)}.blocked-receipt.json"
        if self.domain_store is not None:
            existing_receipt = self.domain_store.get_optional(
                "finance.reconciliation_records", workspace_id=workspace_id,
                entity_id=receipt_entity_id,
            )
            if existing_receipt is not None:
                receipt = dict(existing_receipt["payload"])
                self._verify(receipt, "receipt_hash")
                return receipt
        elif receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8")); self._verify(receipt, "receipt_hash"); return receipt
        receipt = {"schema_version": "aion.xero.reconciliation_execution_receipt.v1",
                   "receipt_id": f"receipt-{handoff_id}", "workspace_id": workspace_id,
                   "handoff_id": handoff_id, "payload_hash": record["payload_hash"],
                   "attempted_by": attempted_by, "attempted_at": attempted_at or _now(),
                   "status": "blocked_provider_capability_unavailable", "code": self.LIMITATION_CODE,
                   "message": "Xero requires bank-statement reconciliation to be completed in Xero Bank Rec or Cash Coding.",
                   "retryable": False, "manual_handoff_required": True,
                   "external_write_performed": False, "provider_reconciliations_posted": 0,
                   "recovery": {"safe_to_retry": False, "next_step": "open_xero_bank_reconciliation"}}
        receipt["receipt_hash"] = canonical_contract_hash(receipt)
        if self.domain_store is not None:
            self.domain_store.put(
                "finance.reconciliation_records", workspace_id=workspace_id,
                entity_id=receipt_entity_id, payload=receipt, expected_version=None,
                actor_id=attempted_by,
            )
        else:
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        record["status"] = "manual_xero_action_required"; record["latest_receipt"] = {
            "receipt_id": receipt["receipt_id"], "receipt_hash": receipt["receipt_hash"],
            **({"vault_domain_id": "finance.reconciliation_records", "vault_entity_id": receipt_entity_id}
               if self.domain_store is not None else {"storage_path": str(receipt_path)})}
        record.pop("handoff_hash", None); record["handoff_hash"] = canonical_contract_hash(record); self._save(workspace_id, record)
        self._index(workspace_id, receipt, receipt_path)
        return receipt

    def load(self, workspace_id: str, handoff_id: str) -> dict[str, Any]:
        if self.domain_store is not None:
            record = self.domain_store.get_optional(
                "finance.reconciliation_records", workspace_id=workspace_id,
                entity_id=f"xero_handoffs/{_safe(handoff_id)}",
            )
            if record is None:
                raise FileNotFoundError(f"Xero reconciliation handoff not found: {handoff_id}")
            value = dict(record["payload"]); self._verify(value, "handoff_hash")
            if value.get("workspace_id") != workspace_id:
                raise PermissionError("xero_reconciliation_handoff_business_isolation_violation")
            return value
        path = self._dir(workspace_id) / f"{_safe(handoff_id)}.json"
        if not path.exists():
            raise FileNotFoundError(f"Xero reconciliation handoff not found: {handoff_id}")
        value = json.loads(path.read_text(encoding="utf-8")); self._verify(value, "handoff_hash")
        if value.get("workspace_id") != workspace_id:
            raise PermissionError("xero_reconciliation_handoff_business_isolation_violation")
        return value

    def list(self, workspace_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if self.domain_store is not None:
            records = []
            for row in self.domain_store.list(
                "finance.reconciliation_records", workspace_id=workspace_id,
            ):
                entity_id = str(row.get("entity_id") or "")
                if not entity_id.startswith("xero_handoffs/") or entity_id.endswith("/blocked_receipt"):
                    continue
                value = dict(row["payload"]); self._verify(value, "handoff_hash")
                records.append(value)
            return sorted(records, key=lambda item: str(item.get("prepared_at") or ""), reverse=True)[:max(1, min(limit, 500))]
        records: list[dict[str, Any]] = []
        paths = sorted(
            (path for path in self._dir(workspace_id).glob("*.json") if not path.name.endswith(".blocked-receipt.json")),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in paths[:max(1, min(limit, 500))]:
            value = json.loads(path.read_text(encoding="utf-8"))
            self._verify(value, "handoff_hash")
            if value.get("workspace_id") != workspace_id:
                raise PermissionError("xero_reconciliation_handoff_business_isolation_violation")
            records.append(value)
        return records

    def _dir(self, workspace_id: str) -> Path:
        if self.domain_store is not None:
            return Path("/__tessaris_guardian_xero_handoffs__") / workspace_id
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/xero_reconciliation_handoffs"
        path.mkdir(parents=True, exist_ok=True); return path

    def _save(self, workspace_id: str, value: dict[str, Any]) -> None:
        if self.domain_store is not None:
            entity_id = f"xero_handoffs/{_safe(value['handoff_id'])}"
            current = self.domain_store.get_optional(
                "finance.reconciliation_records", workspace_id=workspace_id,
                entity_id=entity_id,
            )
            self.domain_store.put(
                "finance.reconciliation_records", workspace_id=workspace_id,
                entity_id=entity_id, payload=value,
                expected_version=int(current["version"]) if current else None,
                actor_id="xero-handoff-runtime",
            )
            return
        path = self._dir(workspace_id) / f"{_safe(value['handoff_id'])}.json"
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _index(self, workspace_id: str, receipt: dict[str, Any], path: Path) -> None:
        tree = WorkflowFileCabinetRepository.load(workspace_id); folders = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        finance = next((item for item in folders if item.get("id") == "folder_finance"), None)
        if finance is None:
            finance = {"id": "folder_finance", "name": "Finance", "type": "department", "children": []}; folders.append(finance)
        children = finance.setdefault("children", []); folder = next((item for item in children if item.get("id") == "folder_finance_xero_reconciliation_handoffs"), None)
        if folder is None:
            folder = {"id": "folder_finance_xero_reconciliation_handoffs", "name": "Xero Reconciliation Handoffs", "type": "folder", "children": []}; children.append(folder)
        folder.setdefault("children", []).append({"id": f"xero_reconciliation_receipt_{receipt['receipt_id']}", "name": receipt["receipt_id"],
            "type": "business_container_artifact", "document_type": "xero_reconciliation_handoff_receipt", "status": receipt["status"],
            "target": ({"vault_domain_id": "finance.reconciliation_records",
                        "vault_entity_id": f"xero_handoffs/{_safe(receipt['handoff_id'])}/blocked_receipt"}
                       if self.domain_store is not None else {"storage_path": str(path)})
                      | {"receipt_hash": receipt["receipt_hash"]}})
        tree["folders"] = folders; tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}
        WorkflowFileCabinetRepository.save(workspace_id, tree)

    @staticmethod
    def _verify(value: dict[str, Any], hash_key: str) -> None:
        expected = value.get(hash_key); payload = dict(value); payload.pop(hash_key, None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError(f"{hash_key}_mismatch")
