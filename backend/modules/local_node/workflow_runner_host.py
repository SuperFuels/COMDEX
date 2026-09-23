from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
import traceback

from backend.modules.local_node.contracts_local_node import (
    ApprovalRecord,
    ApprovalStatus,
    QueueItem,
    QueueItemStatus,
    utc_now_iso,
)
from backend.modules.local_node.local_queue_store import LocalQueueStore
from backend.modules.local_node.local_approval_store import LocalApprovalStore
from backend.modules.local_node.local_audit_store import LocalAuditStore
from backend.modules.local_node.node_state_store import NodeStateStore


@dataclass(slots=True)
class WorkflowRunnerResult:
    ok: bool
    queue_item_id: str
    run_id: Optional[str] = None
    status: str = "unknown"
    detail: Optional[str] = None


class WorkflowRunnerHost:
    """
    Local workflow runner host.

    Responsibilities:
    - pull queued items from the local queue
    - execute them through an injected workflow executor
    - move queue items through queued -> running -> waiting_approval / completed / failed
    - resume approved items through an injected resume executor
    - cancel queued/running/waiting items through an injected cancel executor
    - write audit events
    - keep node_state metrics up to date
    """

    def __init__(
        self,
        *,
        queue_store: LocalQueueStore,
        approval_store: LocalApprovalStore,
        audit_store: LocalAuditStore,
        node_state_store: NodeStateStore,
        execute_workflow: Optional[Callable[[QueueItem], Dict[str, Any]]] = None,
        resume_workflow: Optional[Callable[[QueueItem], Dict[str, Any]]] = None,
        cancel_workflow: Optional[Callable[[QueueItem, str], Dict[str, Any]]] = None,
    ) -> None:
        self.queue_store = queue_store
        self.approval_store = approval_store
        self.audit_store = audit_store
        self.node_state_store = node_state_store

        self.execute_workflow = execute_workflow or self._default_execute_workflow
        self.resume_workflow = resume_workflow or self._default_resume_workflow
        self.cancel_workflow = cancel_workflow or self._default_cancel_workflow

    def _safe_audit(
        self,
        *,
        event_type: str,
        level: str = "info",
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            if hasattr(self.audit_store, "append_event"):
                self.audit_store.append_event(
                    event_type=event_type,
                    level=level,
                    message=message,
                    payload=payload or {},
                )
            elif hasattr(self.audit_store, "append"):
                self.audit_store.append(
                    {
                        "event_type": event_type,
                        "level": level,
                        "message": message,
                        "payload": payload or {},
                        "created_at": utc_now_iso(),
                    }
                )
        except Exception:
            pass

    def _refresh_metrics(self) -> None:
        try:
            items = self.queue_store.list_all()
        except Exception:
            items = []

        queued_count = sum(1 for x in items if x.status == QueueItemStatus.QUEUED.value)
        running_count = sum(1 for x in items if x.status == QueueItemStatus.RUNNING.value)
        waiting_count = sum(
            1 for x in items if x.status == QueueItemStatus.WAITING_APPROVAL.value
        )
        completed_count = sum(1 for x in items if x.status == QueueItemStatus.COMPLETED.value)
        failed_count = sum(1 for x in items if x.status == QueueItemStatus.FAILED.value)
        cancelled_count = sum(1 for x in items if x.status == QueueItemStatus.CANCELLED.value)

        self.node_state_store.save_queue_metrics(
            queued_count=queued_count,
            running_count=running_count,
            waiting_approval_count=waiting_count,
            completed_count=completed_count,
            failed_count=failed_count,
            cancelled_count=cancelled_count,
        )

        pending_approval_count = 0
        approved_count = 0
        rejected_count = 0

        try:
            approvals = self.approval_store.list_all()
            for approval in approvals:
                status = getattr(approval, "status", None)
                if status == ApprovalStatus.PENDING.value:
                    pending_approval_count += 1
                elif status == ApprovalStatus.APPROVED.value:
                    approved_count += 1
                elif status == ApprovalStatus.REJECTED.value:
                    rejected_count += 1
        except Exception:
            pass

        self.node_state_store.save_approval_metrics(
            pending_count=pending_approval_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
        )

    def _default_execute_workflow(self, item: QueueItem) -> Dict[str, Any]:
        """
        Placeholder executor.

        Approval trigger:
        - if item.payload["require_approval"] == True
        - or item.context["require_approval"] == True for older shapes

        Contract returned:
        {
          "status": "completed" | "waiting_approval" | "failed",
          "run_id": "...",
          "detail": "...",
          "approval_request_id": "...",   # when waiting approval
        }
        """
        run_id = item.run_id or f"local-run-{item.id}"

        payload = getattr(item, "payload", None)
        if not isinstance(payload, dict):
            payload = getattr(item, "context", {})
        if not isinstance(payload, dict):
            payload = {}

        require_approval = bool(payload.get("require_approval"))
        brief = payload.get("brief")
        brief_text = brief if isinstance(brief, str) else "Approval-gated workflow"

        if require_approval:
            approval = ApprovalRecord.new(
                workspace_id=getattr(item, "workspace_id", "unknown"),
                run_id=run_id,
                operator_id=getattr(item, "operator_id", "unknown"),
                department_key=getattr(item, "department_key", "unknown"),
                title="Approval required",
                summary=brief_text,
                payload={
                    "queue_item_id": item.id,
                    "run_id": run_id,
                    "workflow_id": getattr(item, "workflow_id", None),
                    "operator_id": getattr(item, "operator_id", None),
                    "department_key": getattr(item, "department_key", None),
                    "draft_brief": brief_text,
                },
                queue_item_id=item.id,
            )
            self.approval_store.upsert(approval)

            return {
                "status": "waiting_approval",
                "run_id": run_id,
                "detail": "Execution paused for approval",
                "approval_request_id": approval.id,
            }

        return {
            "status": "completed",
            "run_id": run_id,
            "detail": "Executed by default local workflow runner host",
        }

    def _default_resume_workflow(self, item: QueueItem) -> Dict[str, Any]:
        return {
            "status": "completed",
            "run_id": item.run_id,
            "detail": "Resumed by default local workflow runner host",
        }

    def _default_cancel_workflow(self, item: QueueItem, reason: str) -> Dict[str, Any]:
        return {
            "status": "cancelled",
            "run_id": item.run_id,
            "detail": reason,
        }

    def get_next_runnable_item(self) -> Optional[QueueItem]:
        return self.queue_store.get_next_queued()

    def run_next(self) -> Optional[WorkflowRunnerResult]:
        item = self.get_next_runnable_item()
        if not item:
            self._refresh_metrics()
            return None

        run_id = item.run_id or f"local-run-{item.id}"

        self.queue_store.mark_running(item.id, run_id=run_id)
        item = self.queue_store.get(item.id)
        if not item:
            self._refresh_metrics()
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=run_id,
                run_id=run_id,
                status="failed",
                detail="Queue item disappeared after mark_running",
            )

        self._safe_audit(
            event_type="local_node.workflow_started",
            message="Workflow execution started",
            payload={
                "queue_item_id": item.id,
                "run_id": run_id,
                "workflow_id": getattr(item, "workflow_id", None),
                "operator_id": getattr(item, "operator_id", None),
                "department_key": getattr(item, "department_key", None),
            },
        )

        try:
            result = self.execute_workflow(item)
            status = str(result.get("status") or "failed")
            result_run_id = result.get("run_id") or run_id
            detail = result.get("detail")

            if status == QueueItemStatus.WAITING_APPROVAL.value or status == "waiting_approval":
                self.queue_store.mark_waiting_approval(item.id)

                approval_request_id = result.get("approval_request_id")
                if approval_request_id:
                    try:
                        self.approval_store.link_queue_item(
                            approval_request_id=approval_request_id,
                            queue_item_id=item.id,
                            run_id=result_run_id,
                        )
                    except Exception:
                        pass

                self._safe_audit(
                    event_type="local_node.workflow_waiting_approval",
                    message="Workflow paused for approval",
                    payload={
                        "queue_item_id": item.id,
                        "run_id": result_run_id,
                        "approval_request_id": approval_request_id,
                        "detail": detail,
                    },
                )

                self._refresh_metrics()
                return WorkflowRunnerResult(
                    ok=True,
                    queue_item_id=item.id,
                    run_id=result_run_id,
                    status="waiting_approval",
                    detail=detail,
                )

            if status == QueueItemStatus.COMPLETED.value or status == "completed":
                self.queue_store.mark_completed(item.id)

                self._safe_audit(
                    event_type="local_node.workflow_completed",
                    message="Workflow execution completed",
                    payload={
                        "queue_item_id": item.id,
                        "run_id": result_run_id,
                        "detail": detail,
                    },
                )

                self._refresh_metrics()
                return WorkflowRunnerResult(
                    ok=True,
                    queue_item_id=item.id,
                    run_id=result_run_id,
                    status="completed",
                    detail=detail,
                )

            failure_detail = detail or f"Workflow returned unexpected status: {status}"
            self.queue_store.mark_failed(item.id, failure_detail)

            self._safe_audit(
                event_type="local_node.workflow_failed",
                level="error",
                message="Workflow execution failed",
                payload={
                    "queue_item_id": item.id,
                    "run_id": result_run_id,
                    "detail": failure_detail,
                },
            )

            self._refresh_metrics()
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=item.id,
                run_id=result_run_id,
                status="failed",
                detail=failure_detail,
            )

        except Exception as exc:
            tb = traceback.format_exc()
            self.queue_store.mark_failed(item.id, str(exc))

            self._safe_audit(
                event_type="local_node.workflow_failed",
                level="error",
                message="Workflow execution raised exception",
                payload={
                    "queue_item_id": item.id,
                    "run_id": run_id,
                    "error": str(exc),
                    "traceback": tb,
                },
            )

            self._refresh_metrics()
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=item.id,
                run_id=run_id,
                status="failed",
                detail=str(exc),
            )

    def resume_approved_item(self, queue_item_id: str) -> WorkflowRunnerResult:
        item = self.queue_store.get(queue_item_id)
        if not item:
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=queue_item_id,
                status="failed",
                detail="Queue item not found",
            )

        if item.status != QueueItemStatus.WAITING_APPROVAL.value:
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=queue_item_id,
                run_id=item.run_id,
                status="failed",
                detail=f"Queue item is not waiting approval: {item.status}",
            )

        self.queue_store.mark_running(item.id, run_id=item.run_id or f"local-run-{item.id}")
        item = self.queue_store.get(item.id)
        if not item:
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=queue_item_id,
                status="failed",
                detail="Queue item disappeared before resume",
            )

        self._safe_audit(
            event_type="local_node.workflow_resume_started",
            message="Workflow resume started",
            payload={
                "queue_item_id": item.id,
                "run_id": item.run_id,
            },
        )

        try:
            result = self.resume_workflow(item)
            status = str(result.get("status") or "failed")
            detail = result.get("detail")
            result_run_id = result.get("run_id") or item.run_id

            if status == QueueItemStatus.COMPLETED.value or status == "completed":
                self.queue_store.mark_completed(item.id)

                self._safe_audit(
                    event_type="local_node.workflow_resumed_completed",
                    message="Workflow resumed and completed",
                    payload={
                        "queue_item_id": item.id,
                        "run_id": result_run_id,
                        "detail": detail,
                    },
                )

                self._refresh_metrics()
                return WorkflowRunnerResult(
                    ok=True,
                    queue_item_id=item.id,
                    run_id=result_run_id,
                    status="completed",
                    detail=detail,
                )

            if status == QueueItemStatus.WAITING_APPROVAL.value or status == "waiting_approval":
                self.queue_store.mark_waiting_approval(item.id)

                self._safe_audit(
                    event_type="local_node.workflow_resumed_waiting_approval",
                    message="Workflow resumed and paused again for approval",
                    payload={
                        "queue_item_id": item.id,
                        "run_id": result_run_id,
                        "detail": detail,
                    },
                )

                self._refresh_metrics()
                return WorkflowRunnerResult(
                    ok=True,
                    queue_item_id=item.id,
                    run_id=result_run_id,
                    status="waiting_approval",
                    detail=detail,
                )

            failure_detail = detail or f"Resume returned unexpected status: {status}"
            self.queue_store.mark_failed(item.id, failure_detail)

            self._safe_audit(
                event_type="local_node.workflow_resume_failed",
                level="error",
                message="Workflow resume failed",
                payload={
                    "queue_item_id": item.id,
                    "run_id": result_run_id,
                    "detail": failure_detail,
                },
            )

            self._refresh_metrics()
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=item.id,
                run_id=result_run_id,
                status="failed",
                detail=failure_detail,
            )

        except Exception as exc:
            tb = traceback.format_exc()
            self.queue_store.mark_failed(item.id, str(exc))

            self._safe_audit(
                event_type="local_node.workflow_resume_failed",
                level="error",
                message="Workflow resume raised exception",
                payload={
                    "queue_item_id": item.id,
                    "run_id": item.run_id,
                    "error": str(exc),
                    "traceback": tb,
                },
            )

            self._refresh_metrics()
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=item.id,
                run_id=item.run_id,
                status="failed",
                detail=str(exc),
            )

    def cancel_item(self, queue_item_id: str, *, reason: str = "cancelled") -> WorkflowRunnerResult:
        item = self.queue_store.get(queue_item_id)
        if not item:
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=queue_item_id,
                status="failed",
                detail="Queue item not found",
            )

        try:
            self.cancel_workflow(item, reason)
        except Exception:
            pass

        cancelled = self.queue_store.mark_cancelled(queue_item_id, reason=reason)
        if not cancelled:
            return WorkflowRunnerResult(
                ok=False,
                queue_item_id=queue_item_id,
                run_id=item.run_id,
                status="failed",
                detail="Unable to cancel queue item",
            )

        self._safe_audit(
            event_type="local_node.workflow_cancelled",
            message="Workflow cancelled",
            payload={
                "queue_item_id": item.id,
                "run_id": item.run_id,
                "reason": reason,
            },
        )

        self._refresh_metrics()
        return WorkflowRunnerResult(
            ok=True,
            queue_item_id=item.id,
            run_id=item.run_id,
            status="cancelled",
            detail=reason,
        )

    def drain_once(self) -> Dict[str, Any]:
        result = self.run_next()
        self._refresh_metrics()

        if result is None:
            return {
                "ok": True,
                "did_work": False,
                "status": "idle",
                "at": utc_now_iso(),
            }

        return {
            "ok": result.ok,
            "did_work": True,
            "queue_item_id": result.queue_item_id,
            "run_id": result.run_id,
            "status": result.status,
            "detail": result.detail,
            "at": utc_now_iso(),
        }

    def get_status(self) -> Dict[str, Any]:
        self._refresh_metrics()
        state = self.node_state_store.get_full_state()

        return {
            "ok": True,
            "runner": {
                "status": "ready",
                "at": utc_now_iso(),
            },
            "state": state,
        }