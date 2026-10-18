from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.local_node.contracts_local_node import LocalNodeConfig, utc_now_iso
from backend.modules.local_node.train_task_approval_store import TrainTaskApprovalStore
from backend.modules.local_node.train_task_store import TrainTaskStore


class GuardianTrainTaskStore:
    AUTOMATION_DOMAIN = "train_agent.automations"
    RUN_DOMAIN = "train_agent.runs_and_audit"

    def __init__(self, workspace_id: str, domain_store: VaultDomainStore) -> None:
        self.workspace_id = str(workspace_id)
        self.domain_store = domain_store

    def _workspace(self, workspace_id: str) -> str:
        if str(workspace_id) != self.workspace_id:
            raise ValueError("train_task_workspace_mismatch")
        return self.workspace_id

    @staticmethod
    def _entity(kind: str, identity: str) -> str:
        value = str(identity or "").strip()
        if not value:
            raise ValueError("train_task_identity_required")
        return f"local_node/{kind}/{value}"

    def _put(self, domain_id: str, entity_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = self.domain_store.get_optional(
            domain_id, workspace_id=self.workspace_id, entity_id=entity_id,
        )
        self.domain_store.put(
            domain_id,
            workspace_id=self.workspace_id,
            entity_id=entity_id,
            payload=payload,
            expected_version=int(current["version"]) if current else None,
            actor_id="local-node-train-agent",
        )
        return payload

    def save_workflow(
        self, workspace_id: str, workflow_id: str, payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        self._workspace(workspace_id)
        now = utc_now_iso()
        current = self.get_workflow(workspace_id, workflow_id) or {}
        record = {
            **payload,
            "workflow_id": workflow_id,
            "workspace_id": workspace_id,
            "created_at": current.get("created_at") or payload.get("created_at") or now,
            "updated_at": now,
        }
        return self._put(
            self.AUTOMATION_DOMAIN, self._entity("workflows", workflow_id), record,
        )

    def get_workflow(self, workspace_id: str, workflow_id: str) -> Optional[Dict[str, Any]]:
        self._workspace(workspace_id)
        row = self.domain_store.get_optional(
            self.AUTOMATION_DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=self._entity("workflows", workflow_id),
        )
        return dict(row["payload"]) if row else None

    def list_workflows(self, workspace_id: str) -> List[Dict[str, Any]]:
        self._workspace(workspace_id)
        prefix = self._entity("workflows", "item").rsplit("/", 1)[0] + "/"
        return [
            dict(row["payload"])
            for row in self.domain_store.list(self.AUTOMATION_DOMAIN, workspace_id=self.workspace_id)
            if str(row.get("entity_id") or "").startswith(prefix)
        ]

    @staticmethod
    def _dedupe_id(dedupe_key: str) -> str:
        return hashlib.sha256(str(dedupe_key).encode("utf-8")).hexdigest()

    def has_seen(self, dedupe_key: str) -> bool:
        if not dedupe_key:
            return False
        return self.domain_store.get_optional(
            self.RUN_DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=self._entity("dedupe", self._dedupe_id(dedupe_key)),
        ) is not None

    def mark_seen(self, dedupe_key: str, payload: Optional[Dict[str, Any]] = None) -> None:
        if not dedupe_key:
            return
        entity_id = self._entity("dedupe", self._dedupe_id(dedupe_key))
        if self.domain_store.get_optional(
            self.RUN_DOMAIN, workspace_id=self.workspace_id, entity_id=entity_id,
        ) is not None:
            return
        self.domain_store.put(
            self.RUN_DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=entity_id,
            payload={"seen_at": utc_now_iso(), "payload": payload or {}},
            expected_version=None,
            actor_id="local-node-train-agent",
        )

    def save_run(
        self, workspace_id: str, run_id: str, payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        self._workspace(workspace_id)
        record = {
            **payload,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "updated_at": utc_now_iso(),
        }
        return self._put(self.RUN_DOMAIN, self._entity("runs", run_id), record)

    def list_runs(self, workspace_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        self._workspace(workspace_id)
        prefix = self._entity("runs", "item").rsplit("/", 1)[0] + "/"
        records = [
            dict(row["payload"])
            for row in self.domain_store.list(self.RUN_DOMAIN, workspace_id=self.workspace_id)
            if str(row.get("entity_id") or "").startswith(prefix)
        ]
        records.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return records[: max(0, int(limit))]


class GuardianTrainTaskApprovalStore:
    DOMAIN = "train_agent.runs_and_audit"

    def __init__(self, workspace_id: str, domain_store: VaultDomainStore) -> None:
        self.workspace_id = str(workspace_id)
        self.domain_store = domain_store

    def _workspace(self, workspace_id: str) -> None:
        if str(workspace_id) != self.workspace_id:
            raise ValueError("train_task_approval_workspace_mismatch")

    @staticmethod
    def _entity(approval_id: str) -> str:
        value = str(approval_id or "").strip()
        if not value:
            raise ValueError("train_task_approval_identity_required")
        return f"local_node/approvals/{value}"

    def save_approval(
        self, workspace_id: str, approval_id: str, payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        self._workspace(workspace_id)
        current = self.get_approval(workspace_id, approval_id) or {}
        now = utc_now_iso()
        record = {
            **payload,
            "approval_id": approval_id,
            "workspace_id": workspace_id,
            "created_at": current.get("created_at") or payload.get("created_at") or now,
            "updated_at": now,
        }
        existing = self.domain_store.get_optional(
            self.DOMAIN, workspace_id=self.workspace_id, entity_id=self._entity(approval_id),
        )
        self.domain_store.put(
            self.DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=self._entity(approval_id),
            payload=record,
            expected_version=int(existing["version"]) if existing else None,
            actor_id="local-node-train-agent-approval",
        )
        return record

    def get_approval(
        self, workspace_id: str, approval_id: str,
    ) -> Optional[Dict[str, Any]]:
        self._workspace(workspace_id)
        row = self.domain_store.get_optional(
            self.DOMAIN, workspace_id=self.workspace_id, entity_id=self._entity(approval_id),
        )
        return dict(row["payload"]) if row else None

    def list_approvals(
        self, workspace_id: str, *, status: Optional[str] = None, limit: int = 50,
    ) -> List[Dict[str, Any]]:
        self._workspace(workspace_id)
        prefix = "local_node/approvals/"
        records = [
            dict(row["payload"])
            for row in self.domain_store.list(self.DOMAIN, workspace_id=self.workspace_id)
            if str(row.get("entity_id") or "").startswith(prefix)
            and (not status or str((row.get("payload") or {}).get("status") or "") == status)
        ]
        records.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return records[: max(1, min(int(limit or 50), 500))]


def configured_local_node_train_task_stores(config: LocalNodeConfig):
    if guardian_mode_requested():
        runtime = configured_business_vault_runtime()
        domains = VaultDomainStore(runtime.guardian, actor_id="local-node-train-agent")
        return (
            GuardianTrainTaskStore(config.workspace_id, domains),
            GuardianTrainTaskApprovalStore(config.workspace_id, domains),
        )
    runtime_mode = str(os.getenv("TESSARIS_RUNTIME_MODE") or "development").strip().lower()
    if runtime_mode in {"production", "prod"}:
        raise RuntimeError("local_node_guardian_train_task_store_required_in_production")
    return TrainTaskStore(config.base_dir), TrainTaskApprovalStore(config.base_dir)


def migrate_local_node_train_task_stores(
    config: LocalNodeConfig,
    *,
    task_target: GuardianTrainTaskStore,
    approval_target: GuardianTrainTaskApprovalStore,
) -> dict[str, object]:
    source = TrainTaskStore(config.base_dir)
    approvals = TrainTaskApprovalStore(config.base_dir)
    counts = {"workflows": 0, "runs": 0, "approvals": 0, "dedupe": 0}
    for workflow in source.list_workflows(config.workspace_id):
        workflow_id = str(workflow.get("workflow_id") or "")
        task_target.save_workflow(config.workspace_id, workflow_id, workflow)
        if task_target.get_workflow(config.workspace_id, workflow_id) is None:
            raise RuntimeError("train_task_workflow_migration_verify_failed")
        counts["workflows"] += 1
    for run in source.list_runs(config.workspace_id, limit=1_000_000):
        run_id = str(run.get("run_id") or "")
        task_target.save_run(config.workspace_id, run_id, run)
        counts["runs"] += 1
    dedupe = source._read_dedupe()
    for key, value in dedupe.items():
        task_target.mark_seen(str(key), dict(value) if isinstance(value, dict) else {"value": value})
        if not task_target.has_seen(str(key)):
            raise RuntimeError("train_task_dedupe_migration_verify_failed")
        counts["dedupe"] += 1
    for approval in approvals.list_approvals(config.workspace_id, limit=1_000_000):
        approval_id = str(approval.get("approval_id") or "")
        approval_target.save_approval(config.workspace_id, approval_id, approval)
        if approval_target.get_approval(config.workspace_id, approval_id) is None:
            raise RuntimeError("train_task_approval_migration_verify_failed")
        counts["approvals"] += 1
    return {
        "schema_version": "tessaris.local-node-train-task-migration.v1",
        "workspace_id": config.workspace_id,
        "copied_and_verified": counts,
        "source_retained": True,
    }
