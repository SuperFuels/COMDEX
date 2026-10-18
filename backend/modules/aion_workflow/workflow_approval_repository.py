from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import json
import re
import uuid

from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_agents.runtime.vault_repository_backend import (
    AgentVaultRepositoryBackend,
    configured_agent_domain_store,
)


SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _safe_id(value: str, fallback: str) -> str:
    raw = str(value or fallback).strip() or fallback
    return SAFE_ID_RE.sub("-", raw).strip("-") or fallback


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WorkflowApprovalRepository:
    def __init__(
        self,
        runtime_root: Path | str | None = None,
        *,
        domain_store: VaultDomainStore | None = None,
    ) -> None:
        self.runtime_root = Path(runtime_root or ".runtime/local_node")
        store = domain_store or (
            configured_agent_domain_store() if runtime_root is None else None
        )
        self.vault = (
            AgentVaultRepositoryBackend(store, kind="workflow_approvals", audit=True)
            if store
            else None
        )

    def approval_dir(self, business_container: str, workflow_id: str) -> Path:
        safe_business = _safe_id(business_container, "costa-conexion")
        safe_workflow = _safe_id(workflow_id, "workflow_draft_1")
        return self.runtime_root / safe_business / "aion_workflow_approvals" / safe_workflow

    def approval_path(self, business_container: str, workflow_id: str, approval_id: str) -> Path:
        safe_approval = _safe_id(approval_id, "approval_unknown")
        return self.approval_dir(business_container, workflow_id) / f"{safe_approval}.json"

    def create(
        self,
        *,
        business_container: str,
        workflow_id: str,
        approval_node_id: str,
        approval_title: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        now = utc_now_iso()
        approval_id = f"approval_{uuid.uuid4().hex[:16]}"

        record = {
            "schema_version": "aion.workflow_approval.v1",
            "approval_id": approval_id,
            "business_container": _safe_id(business_container, "costa-conexion"),
            "workflow_id": _safe_id(workflow_id, "workflow_draft_1"),
            "approval_node_id": str(approval_node_id),
            "approval_title": str(approval_title or "Human approval"),
            "status": "pending",
            "decision": None,
            "payload": payload,
            "created_at": now,
            "updated_at": now,
            "decided_at": None,
        }

        if self.vault is not None:
            self.vault.put(
                workspace_id=record["business_container"],
                item_id=approval_id,
                payload=record,
            )
            record["path"] = (
                "vault://train_agent.runs_and_audit/workflow_approvals/"
                + approval_id
            )
            return record

        path = self.approval_path(record["business_container"], record["workflow_id"], approval_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

        record["path"] = str(path)
        return record

    def load(self, business_container: str, workflow_id: str, approval_id: str) -> dict[str, Any] | None:
        if self.vault is not None:
            record = self.vault.get(
                workspace_id=_safe_id(business_container, "costa-conexion"),
                item_id=_safe_id(approval_id, "approval_unknown"),
            )
            if record is None:
                return None
            if record.get("workflow_id") != _safe_id(workflow_id, "workflow_draft_1"):
                return None
            record["path"] = (
                "vault://train_agent.runs_and_audit/workflow_approvals/"
                + str(record["approval_id"])
            )
            return record
        path = self.approval_path(business_container, workflow_id, approval_id)
        if not path.exists():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        record["path"] = str(path)
        return record

    def decide(
        self,
        *,
        business_container: str,
        workflow_id: str,
        approval_id: str,
        decision: str,
        reason: str = "",
    ) -> dict[str, Any]:
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")

        record = self.load(business_container, workflow_id, approval_id)
        if record is None:
            raise FileNotFoundError("Approval request not found")

        now = utc_now_iso()
        record["status"] = decision
        record["decision"] = decision
        record["reason"] = reason
        record["updated_at"] = now
        record["decided_at"] = now

        clean_record = {k: v for k, v in record.items() if k != "path"}
        if self.vault is not None:
            self.vault.put(
                workspace_id=record["business_container"],
                item_id=record["approval_id"],
                payload=clean_record,
            )
            record["path"] = (
                "vault://train_agent.runs_and_audit/workflow_approvals/"
                + record["approval_id"]
            )
            return record

        path = Path(record["path"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(clean_record, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

        record["path"] = str(path)
        return record
