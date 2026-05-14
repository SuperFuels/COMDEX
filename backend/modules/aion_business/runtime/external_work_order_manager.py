from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.modules.aion_business.contracts.external_work_orders import (
    ExternalWorkOrderRecord,
)
from backend.modules.aion_business.runtime.audit_log import AuditLog
from backend.modules.aion_business.runtime.external_specialist_registry import (
    ExternalSpecialistRegistry,
)
from backend.modules.aion_business.runtime.external_work_order_repository import (
    ExternalWorkOrderRepository,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ExternalWorkOrderManager:
    def __init__(
        self,
        *,
        registry: Optional[ExternalSpecialistRegistry] = None,
        repository: Optional[ExternalWorkOrderRepository] = None,
        audit_log: Optional[AuditLog] = None,
    ):
        self.registry = registry or ExternalSpecialistRegistry()
        self.repository = repository or ExternalWorkOrderRepository()
        self.audit_log = audit_log or AuditLog()

    def create_work_order(
        self,
        *,
        workspace_id: str,
        capability: str,
        objective: str,
        parent_task_id: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExternalWorkOrderRecord:
        selection = self.registry.resolve_for_capability(
            workspace_id=workspace_id,
            capability=capability,
        )

        specialist = None
        if selection.selected_specialist_id:
            specialist = self.registry.load(workspace_id, selection.selected_specialist_id)

        record = ExternalWorkOrderRecord(
            id=f"ewo-{secrets.token_hex(6)}",
            workspace_id=workspace_id,
            parent_task_id=parent_task_id,
            capability=capability,
            objective=objective,
            specialist_id=specialist.id if specialist else None,
            specialist_provider=specialist.provider if specialist else None,
            status="queued",
            priority=priority,
            inputs=inputs or {},
            metadata={
                "selection_reason": selection.reason,
                "fallback_specialist_ids": selection.fallback_specialist_ids,
                **(metadata or {}),
            },
        )

        self.repository.save(record)

        self.audit_log.log_event(
            workspace_id=workspace_id,
            event_type="custom",
            task_id=parent_task_id,
            summary="External work order created",
            payload=record.model_dump(mode="json"),
            tags=["external_work_order", "created", capability],
        )

        return record

    def dispatch(self, workspace_id: str, work_order_id: str) -> ExternalWorkOrderRecord:
        record = self.repository.load(workspace_id, work_order_id)
        record.status = "dispatched"
        record.updated_at = utc_now_iso()
        self.repository.save(record)

        self.audit_log.log_event(
            workspace_id=workspace_id,
            event_type="custom",
            task_id=record.parent_task_id,
            summary="External work order dispatched",
            payload={"work_order_id": record.id},
            tags=["external_work_order", "dispatched"],
        )
        return record

    def complete(
        self,
        workspace_id: str,
        work_order_id: str,
        *,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> ExternalWorkOrderRecord:
        record = self.repository.load(workspace_id, work_order_id)
        record.status = "completed"
        record.outputs = outputs or {}
        record.updated_at = utc_now_iso()
        record.completed_at = utc_now_iso()
        self.repository.save(record)

        self.audit_log.log_event(
            workspace_id=workspace_id,
            event_type="custom",
            task_id=record.parent_task_id,
            summary="External work order completed",
            payload={"work_order_id": record.id},
            tags=["external_work_order", "completed"],
        )
        return record

    def fail(
        self,
        workspace_id: str,
        work_order_id: str,
        *,
        error_code: str,
    ) -> ExternalWorkOrderRecord:
        record = self.repository.load(workspace_id, work_order_id)
        record.status = "failed"
        record.outputs["error_code"] = error_code
        record.updated_at = utc_now_iso()
        self.repository.save(record)

        self.audit_log.log_event(
            workspace_id=workspace_id,
            event_type="custom",
            task_id=record.parent_task_id,
            summary="External work order failed",
            payload={"work_order_id": record.id, "error_code": error_code},
            tags=["external_work_order", "failed"],
        )
        return record