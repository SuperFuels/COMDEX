from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.modules.local_node.contracts_cloud_sync import (
    CloudSyncAuditSummaryItem,
    CloudSyncApprovalItem,
    CloudSyncNodeHealth,
    CloudSyncPullResponse,
    CloudSyncPushRequest,
    CloudSyncQueueItem,
    CloudSyncRemoteCommand,
)
from backend.modules.local_node.contracts_local_node import utc_now_iso
from backend.modules.local_node.local_queue_store import LocalQueueStore
from backend.modules.local_node.local_approval_store import LocalApprovalStore
from backend.modules.local_node.local_audit_store import LocalAuditStore
from backend.modules.local_node.node_state_store import NodeStateStore
from backend.modules.local_node.sync_cursor_store import SyncCursorStore


class LocalSyncEndpoints:
    """
    Local adapter that prepares sync payloads and applies pulled remote commands.

    This does not perform HTTP itself.
    It gives the runtime a clean contract for:
    - building cloud push payloads
    - applying cloud pull commands
    - maintaining cursors/ack tokens
    """

    def __init__(
        self,
        *,
        node_id: str,
        workspace_id: str,
        deployment_mode: str,
        queue_store: LocalQueueStore,
        approval_store: LocalApprovalStore,
        audit_store: LocalAuditStore,
        node_state_store: NodeStateStore,
        sync_cursor_store: SyncCursorStore,
    ) -> None:
        self.node_id = node_id
        self.workspace_id = workspace_id
        self.deployment_mode = deployment_mode
        self.queue_store = queue_store
        self.approval_store = approval_store
        self.audit_store = audit_store
        self.node_state_store = node_state_store
        self.sync_cursor_store = sync_cursor_store

    def _append_audit(
        self,
        *,
        event_type: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
        level: str = "info",
    ) -> None:
        try:
            self.audit_store.append_event(
                event_type=event_type,
                message=message,
                payload=payload or {},
                level=level,
            )
        except Exception:
            pass

    def build_push_request(self) -> CloudSyncPushRequest:
        queue_items: List[CloudSyncQueueItem] = []
        for item in self.queue_store.list_all():
            queue_items.append(
                CloudSyncQueueItem(
                    id=item.id,
                    workflow_id=item.workflow_id,
                    operator_id=item.operator_id,
                    department_key=item.department_key,
                    status=item.status,
                    run_id=item.run_id,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    started_at=item.started_at,
                    completed_at=item.completed_at,
                    failure_reason=item.failure_reason,
                    workspace_id=self.workspace_id,
                )
            )

        approvals: List[CloudSyncApprovalItem] = []
        for approval in self.approval_store.list_all():
            approvals.append(
                CloudSyncApprovalItem(
                    id=approval.id,
                    queue_item_id=getattr(approval, "queue_item_id", None),
                    run_id=getattr(approval, "run_id", None),
                    status=approval.status,
                    requested_at=approval.requested_at,
                    resolved_at=getattr(approval, "resolved_at", None),
                    resolved_by=getattr(approval, "resolved_by", None),
                    resolution_note=getattr(approval, "resolution_note", None),
                    workspace_id=self.workspace_id,
                )
            )

        state = self.node_state_store.get_full_state()
        queue_metrics = state.get("queue_metrics", {})
        approval_metrics = state.get("approval_metrics", {})
        heartbeat = state.get("heartbeat", {})

        heartbeat_at = (
            heartbeat.get("last_heartbeat_at")
            or heartbeat.get("recorded_at")
            or utc_now_iso()
        )

        node_health = CloudSyncNodeHealth(
            node_id=self.node_id,
            workspace_id=self.workspace_id,
            deployment_mode=self.deployment_mode,
            status=str(heartbeat.get("status") or "unknown"),
            heartbeat_at=str(heartbeat_at),
            started_at=heartbeat.get("started_at"),
            queue_depth=int(queue_metrics.get("queued_count") or 0),
            running_count=int(queue_metrics.get("running_count") or 0),
            waiting_approval_count=int(
                queue_metrics.get("waiting_approval_count")
                or approval_metrics.get("pending_count")
                or 0
            ),
            failed_count=int(queue_metrics.get("failed_count") or 0),
            last_error=heartbeat.get("last_error"),
            metadata={
                "completed_count": int(queue_metrics.get("completed_count") or 0),
                "cancelled_count": int(queue_metrics.get("cancelled_count") or 0),
                "approved_count": int(approval_metrics.get("approved_count") or 0),
                "rejected_count": int(approval_metrics.get("rejected_count") or 0),
            },
        )

        audit_summaries: List[CloudSyncAuditSummaryItem] = []
        if hasattr(self.audit_store, "list_recent"):
            recent = self.audit_store.list_recent(limit=100)
        elif hasattr(self.audit_store, "list_all"):
            recent = self.audit_store.list_all()[-100:]
        else:
            recent = []

        for event in recent:
            event_id = getattr(event, "id", None) or str(
                getattr(event, "created_at", utc_now_iso())
            )
            audit_summaries.append(
                CloudSyncAuditSummaryItem(
                    id=str(event_id),
                    event_type=str(getattr(event, "event_type", "unknown")),
                    level=str(getattr(event, "level", "info")),
                    created_at=str(getattr(event, "created_at", utc_now_iso())),
                    message=str(getattr(event, "message", "")),
                    run_id=getattr(event, "run_id", None),
                    queue_item_id=getattr(event, "queue_item_id", None),
                )
            )

        return CloudSyncPushRequest(
            node_id=self.node_id,
            workspace_id=self.workspace_id,
            pushed_at=utc_now_iso(),
            queue_items=queue_items,
            approvals=approvals,
            node_health=node_health,
            audit_summaries=audit_summaries,
            ack_token=self.sync_cursor_store.get_last_ack_token(),
        )

    def mark_push_success(self, *, pushed_at: str, ack_token: str | None = None) -> None:
        self.sync_cursor_store.set_last_push_at(pushed_at)
        self.sync_cursor_store.set_last_success_at(pushed_at)
        self.sync_cursor_store.clear_last_error()

        sync_state = self.node_state_store.get_sync_state()
        sync_state.update(
            {
                "last_push_at": pushed_at,
                "last_success_at": pushed_at,
                "last_ack_token": ack_token or sync_state.get("last_ack_token"),
                "last_error": None,
                "pending_upload_count": 0,
                "updated_at": utc_now_iso(),
            }
        )
        self.node_state_store.save_sync_state(sync_state)

        if ack_token:
            self.sync_cursor_store.set_last_ack_token(ack_token)

    def mark_pull_success(self, *, pulled_at: str, ack_token: str | None = None) -> None:
        self.sync_cursor_store.set_last_pull_at(pulled_at)
        self.sync_cursor_store.set_last_success_at(pulled_at)
        self.sync_cursor_store.clear_last_error()

        sync_state = self.node_state_store.get_sync_state()
        sync_state.update(
            {
                "last_pull_at": pulled_at,
                "last_success_at": pulled_at,
                "last_ack_token": ack_token or sync_state.get("last_ack_token"),
                "last_error": None,
                "pending_download_count": 0,
                "updated_at": utc_now_iso(),
            }
        )
        self.node_state_store.save_sync_state(sync_state)

        if ack_token:
            self.sync_cursor_store.set_last_ack_token(ack_token)

    def mark_sync_error(self, error: str) -> None:
        self.sync_cursor_store.set_last_error(error)

        sync_state = self.node_state_store.get_sync_state()
        sync_state.update(
            {
                "last_error": error,
                "updated_at": utc_now_iso(),
            }
        )
        self.node_state_store.save_sync_state(sync_state)

    def build_pull_response(
        self,
        *,
        commands: List[Dict[str, Any]] | None = None,
        ack_token: str | None = None,
    ) -> CloudSyncPullResponse:
        out_commands: List[CloudSyncRemoteCommand] = []

        for raw in commands or []:
            out_commands.append(
                CloudSyncRemoteCommand(
                    id=str(raw.get("id") or ""),
                    command_type=str(raw.get("command_type") or ""),
                    target_id=raw.get("target_id"),
                    payload=raw.get("payload") or {},
                    issued_at=str(raw.get("issued_at") or utc_now_iso()),
                )
            )

        return CloudSyncPullResponse(
            ok=True,
            pulled_at=utc_now_iso(),
            ack_token=ack_token,
            commands=out_commands,
        )

    def apply_remote_commands(
        self,
        commands: List[CloudSyncRemoteCommand],
    ) -> List[Dict[str, Any]]:
        """
        Applies only storage/control-side effects here.
        The runtime performs the actual execution actions.
        """
        results: List[Dict[str, Any]] = []

        for command in commands:
            command_type = (command.command_type or "").strip()
            target_id = command.target_id
            payload = command.payload or {}
            requested_by = str(payload.get("requested_by") or "cloud")
            reason = payload.get("reason")

            if command_type == "pause":
                self.node_state_store.set_control_state(
                    command="pause",
                    requested_by=requested_by,
                    reason=reason,
                )
                self._append_audit(
                    event_type="local_node.remote_pause_requested",
                    message="Remote pause requested",
                    payload={
                        "command_id": command.id,
                        "reason": reason,
                        "requested_by": requested_by,
                    },
                )
                results.append(
                    {
                        "command_id": command.id,
                        "command_type": command_type,
                        "ok": True,
                        "detail": "Pause request recorded",
                    }
                )
                continue

            if command_type == "resume":
                self.node_state_store.set_control_state(
                    command="resume",
                    requested_by=requested_by,
                    reason=reason,
                )
                self._append_audit(
                    event_type="local_node.remote_resume_requested",
                    message="Remote resume requested",
                    payload={
                        "command_id": command.id,
                        "reason": reason,
                        "requested_by": requested_by,
                    },
                )
                results.append(
                    {
                        "command_id": command.id,
                        "command_type": command_type,
                        "ok": True,
                        "detail": "Resume request recorded",
                    }
                )
                continue

            if command_type == "cancel_run":
                self._append_audit(
                    event_type="local_node.remote_cancel_requested",
                    message="Remote run cancel requested",
                    payload={
                        "command_id": command.id,
                        "target_id": target_id,
                        "reason": reason,
                        "requested_by": requested_by,
                    },
                )
                results.append(
                    {
                        "command_id": command.id,
                        "command_type": command_type,
                        "ok": True,
                        "target_id": target_id,
                        "detail": "Cancel request accepted for runtime execution",
                    }
                )
                continue

            if command_type == "resume_approval":
                self._append_audit(
                    event_type="local_node.remote_resume_approval_requested",
                    message="Remote approval resume requested",
                    payload={
                        "command_id": command.id,
                        "target_id": target_id,
                        "requested_by": requested_by,
                    },
                )
                results.append(
                    {
                        "command_id": command.id,
                        "command_type": command_type,
                        "ok": True,
                        "target_id": target_id,
                        "detail": "Approval resume request accepted for runtime execution",
                    }
                )
                continue

            results.append(
                {
                    "command_id": command.id,
                    "command_type": command_type,
                    "ok": False,
                    "target_id": target_id,
                    "detail": "Unsupported remote command",
                }
            )

        return results