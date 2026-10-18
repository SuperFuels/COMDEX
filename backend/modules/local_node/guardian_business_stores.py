from __future__ import annotations

import os
from typing import Optional

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.department_operational_store import (
    BusinessOperationsRecordRepository,
    DepartmentOperationalStore,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.local_node.contracts_local_node import (
    ApprovalRecord,
    ApprovalStatus,
    AuditEvent,
    LocalNodeConfig,
    QueueItem,
    QueueItemStatus,
    utc_now_iso,
)
from backend.modules.local_node.local_approval_store import LocalApprovalStore
from backend.modules.local_node.local_audit_store import LocalAuditStore
from backend.modules.local_node.local_queue_store import LocalQueueStore


class GuardianLocalQueueStore:
    def __init__(self, workspace_id: str, repository: BusinessOperationsRecordRepository) -> None:
        self.workspace_id = str(workspace_id)
        self.repository = repository

    def _check_workspace(self, workspace_id: str) -> None:
        if str(workspace_id) != self.workspace_id:
            raise ValueError("local_node_queue_workspace_mismatch")

    def upsert(self, item: QueueItem) -> None:
        self._check_workspace(item.workspace_id)
        self.repository.put(
            self.workspace_id, item.id, item.to_dict(), actor_id="local-node-queue",
        )

    enqueue = upsert

    def get(self, item_id: str) -> Optional[QueueItem]:
        record = self.repository.get_optional(self.workspace_id, item_id)
        return QueueItem.from_dict(dict(record["payload"])) if record else None

    def list_all(self) -> list[QueueItem]:
        return [
            QueueItem.from_dict(dict(row["payload"]))
            for row in self.repository.list_workspace(self.workspace_id)
        ]

    def list_by_status(self, status: str) -> list[QueueItem]:
        return [item for item in self.list_all() if item.status == status]

    def get_next_queued(self) -> Optional[QueueItem]:
        queued = sorted(
            self.list_by_status(QueueItemStatus.QUEUED.value), key=lambda item: item.created_at,
        )
        return queued[0] if queued else None

    def mark_running(self, item_id: str, *, run_id: str) -> Optional[QueueItem]:
        item = self.get(item_id)
        if not item:
            return None
        item.status, item.run_id = QueueItemStatus.RUNNING.value, run_id
        item.started_at = item.updated_at = utc_now_iso()
        self.upsert(item)
        return item

    def mark_waiting_approval(self, item_id: str) -> Optional[QueueItem]:
        item = self.get(item_id)
        if not item:
            return None
        item.status, item.updated_at = QueueItemStatus.WAITING_APPROVAL.value, utc_now_iso()
        self.upsert(item)
        return item

    def _finish(self, item_id: str, status: str, reason: str | None = None) -> Optional[QueueItem]:
        item = self.get(item_id)
        if not item:
            return None
        item.status, item.failure_reason = status, reason
        item.completed_at = item.updated_at = utc_now_iso()
        self.upsert(item)
        return item

    def mark_completed(self, item_id: str) -> Optional[QueueItem]:
        return self._finish(item_id, QueueItemStatus.COMPLETED.value)

    def mark_failed(self, item_id: str, reason: str) -> Optional[QueueItem]:
        return self._finish(item_id, QueueItemStatus.FAILED.value, reason)

    def mark_cancelled(self, item_id: str, reason: str = "cancelled") -> Optional[QueueItem]:
        return self._finish(item_id, QueueItemStatus.CANCELLED.value, reason)

    def count_running(self) -> int:
        return len(self.list_by_status(QueueItemStatus.RUNNING.value))

    def count_pending(self) -> int:
        return len(self.list_by_status(QueueItemStatus.QUEUED.value))


class GuardianLocalApprovalStore:
    def __init__(self, workspace_id: str, repository: BusinessOperationsRecordRepository) -> None:
        self.workspace_id = str(workspace_id)
        self.repository = repository

    def upsert(self, approval: ApprovalRecord) -> None:
        if str(approval.workspace_id) != self.workspace_id:
            raise ValueError("local_node_approval_workspace_mismatch")
        self.repository.put(
            self.workspace_id,
            approval.id,
            approval.to_dict(),
            actor_id="local-node-approval",
        )

    def get(self, approval_id: str) -> Optional[ApprovalRecord]:
        record = self.repository.get_optional(self.workspace_id, approval_id)
        return ApprovalRecord.from_dict(dict(record["payload"])) if record else None

    def list_all(self) -> list[ApprovalRecord]:
        return [
            ApprovalRecord.from_dict(dict(row["payload"]))
            for row in self.repository.list_workspace(self.workspace_id)
        ]

    def list_pending(self) -> list[ApprovalRecord]:
        return [item for item in self.list_all() if item.status == ApprovalStatus.PENDING.value]

    def resolve(
        self,
        approval_id: str,
        *,
        approve: bool,
        resolved_by: str,
        resolution_note: Optional[str] = None,
    ) -> Optional[ApprovalRecord]:
        approval = self.get(approval_id)
        if not approval:
            return None
        approval.status = ApprovalStatus.APPROVED.value if approve else ApprovalStatus.REJECTED.value
        approval.resolved_at, approval.resolved_by = utc_now_iso(), resolved_by
        approval.resolution_note = resolution_note
        self.upsert(approval)
        return approval

    def link_queue_item(
        self, *, approval_request_id: str, queue_item_id: str, run_id: Optional[str] = None,
    ) -> Optional[ApprovalRecord]:
        approval = self.get(approval_request_id)
        if not approval:
            return None
        approval.queue_item_id = queue_item_id
        if run_id:
            approval.run_id = run_id
        self.upsert(approval)
        return approval


class GuardianLocalAuditStore:
    DEPARTMENT_ID = "business_operations"
    FEATURE_ID = "local_node_audit"

    def __init__(self, workspace_id: str, operational_store: DepartmentOperationalStore) -> None:
        self.workspace_id = str(workspace_id)
        self.operational_store = operational_store

    def get(self, event_id: str) -> Optional[AuditEvent]:
        for row in self.operational_store.list_audit(
            workspace_id=self.workspace_id,
            department_id=self.DEPARTMENT_ID,
            feature_id=self.FEATURE_ID,
        ):
            if str(row.get("entity_id") or "").endswith("/" + event_id):
                return AuditEvent.from_dict(dict(row["payload"]))
        return None

    def upsert(self, event: AuditEvent) -> None:
        if str(event.workspace_id) != self.workspace_id:
            raise ValueError("local_node_audit_workspace_mismatch")
        existing = self.get(event.id)
        if existing:
            if existing.to_dict() != event.to_dict():
                raise ValueError("local_node_audit_event_immutable")
            return
        self.operational_store.append_audit(
            workspace_id=self.workspace_id,
            department_id=self.DEPARTMENT_ID,
            feature_id=self.FEATURE_ID,
            event_id=event.id,
            payload=event.to_dict(),
            actor_id="local-node-audit",
        )

    append = upsert

    def append_event(
        self,
        *,
        event_type: str,
        message: str,
        payload: Optional[dict] = None,
        level: str = "info",
        node_id: str = "node_mac_local_01",
        workspace_id: str | None = None,
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
        queue_item_id: Optional[str] = None,
        approval_id: Optional[str] = None,
    ) -> AuditEvent:
        workspace = workspace_id or self.workspace_id
        event = AuditEvent.new(
            node_id=node_id,
            workspace_id=workspace,
            event_type=event_type,
            level=level,
            message=message,
            payload=payload or {},
            trace_id=trace_id,
            run_id=run_id,
            queue_item_id=queue_item_id,
            approval_id=approval_id,
        )
        self.upsert(event)
        return event

    def list_all(self) -> list[AuditEvent]:
        rows = self.operational_store.list_audit(
            workspace_id=self.workspace_id,
            department_id=self.DEPARTMENT_ID,
            feature_id=self.FEATURE_ID,
        )
        return [AuditEvent.from_dict(dict(row["payload"])) for row in rows]

    def list_recent(self, limit: int = 100) -> list[AuditEvent]:
        return list(reversed(self.list_all()[-max(0, int(limit)) :]))

    tail = list_recent


def configured_local_node_business_stores(config: LocalNodeConfig):
    """Select Guardian business stores or explicit development legacy stores."""

    if guardian_mode_requested():
        runtime = configured_business_vault_runtime()
        domain_store = VaultDomainStore(runtime.guardian, actor_id="local-node-runtime")
        operational_store = DepartmentOperationalStore(domain_store=domain_store)
        return (
            GuardianLocalQueueStore(
                config.workspace_id,
                BusinessOperationsRecordRepository(
                    "local_node_queue", operational_store=operational_store,
                ),
            ),
            GuardianLocalApprovalStore(
                config.workspace_id,
                BusinessOperationsRecordRepository(
                    "local_node_approvals", operational_store=operational_store,
                ),
            ),
            GuardianLocalAuditStore(config.workspace_id, operational_store),
        )
    runtime_mode = str(os.getenv("TESSARIS_RUNTIME_MODE") or "development").strip().lower()
    if runtime_mode in {"production", "prod"}:
        raise RuntimeError("local_node_guardian_business_store_required_in_production")
    return (
        LocalQueueStore(config.base_dir),
        LocalApprovalStore(config.base_dir),
        LocalAuditStore(config.base_dir),
    )


def migrate_local_node_business_stores(
    config: LocalNodeConfig,
    *,
    queue_target: GuardianLocalQueueStore,
    approval_target: GuardianLocalApprovalStore,
    audit_target: GuardianLocalAuditStore,
) -> dict[str, object]:
    """Copy and verify legacy Node business records without deleting the sources."""

    queue_source = LocalQueueStore(config.base_dir)
    approval_source = LocalApprovalStore(config.base_dir)
    audit_source = LocalAuditStore(config.base_dir)
    counts = {"queue": 0, "approvals": 0, "audit": 0}
    for item in queue_source.list_all():
        queue_target.upsert(item)
        if queue_target.get(item.id).to_dict() != item.to_dict():
            raise RuntimeError("local_node_queue_migration_verify_failed")
        counts["queue"] += 1
    for approval in approval_source.list_all():
        approval_target.upsert(approval)
        if approval_target.get(approval.id).to_dict() != approval.to_dict():
            raise RuntimeError("local_node_approval_migration_verify_failed")
        counts["approvals"] += 1
    for event in audit_source.list_all():
        audit_target.append(event)
        if audit_target.get(event.id).to_dict() != event.to_dict():
            raise RuntimeError("local_node_audit_migration_verify_failed")
        counts["audit"] += 1
    return {
        "schema_version": "tessaris.local-node-business-migration.v1",
        "workspace_id": config.workspace_id,
        "copied_and_verified": counts,
        "source_retained": True,
    }
