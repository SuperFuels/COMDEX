from __future__ import annotations

from typing import Any, Dict, Optional
import uuid

from backend.modules.local_node.contracts_local_node import (
    QueueItem,
    QueueItemStatus,
    utc_now_iso,
)
from backend.modules.local_node.node_state_store import NodeStateStore


class LocalNodeControl:
    def __init__(
        self,
        *,
        node_id: str,
        workspace_id: str,
        node_state_store: NodeStateStore,
    ) -> None:
        self.node_id = node_id
        self.workspace_id = workspace_id
        self.node_state_store = node_state_store

        existing = self.node_state_store.get_runtime_flags()
        if not existing:
            self.set_stopped(reason="initialized")

    def set_running(self) -> Dict[str, Any]:
        self.node_state_store.save_runtime_flags(
            is_running=True,
            is_paused=False,
            is_stopped=False,
            pause_reason=None,
            stop_reason=None,
        )
        self.node_state_store.set_control_state(
            command="running",
            requested_by="system",
            reason=None,
        )
        return self.get_status()

    def pause(
        self,
        *,
        reason: Optional[str] = None,
        requested_by: str = "system",
    ) -> Dict[str, Any]:
        self.node_state_store.save_runtime_flags(
            is_running=False,
            is_paused=True,
            is_stopped=False,
            pause_reason=reason,
            stop_reason=None,
        )
        self.node_state_store.set_control_state(
            command="pause",
            requested_by=requested_by,
            reason=reason,
        )
        return self.get_status()

    def resume(
        self,
        *,
        reason: Optional[str] = None,
        requested_by: str = "system",
    ) -> Dict[str, Any]:
        self.node_state_store.save_runtime_flags(
            is_running=True,
            is_paused=False,
            is_stopped=False,
            pause_reason=None,
            stop_reason=None,
        )
        self.node_state_store.set_control_state(
            command="resume",
            requested_by=requested_by,
            reason=reason,
        )
        return self.get_status()

    def set_stopped(
        self,
        *,
        reason: Optional[str] = None,
        requested_by: str = "system",
    ) -> Dict[str, Any]:
        self.node_state_store.save_runtime_flags(
            is_running=False,
            is_paused=False,
            is_stopped=True,
            pause_reason=None,
            stop_reason=reason,
        )
        self.node_state_store.set_control_state(
            command="stop",
            requested_by=requested_by,
            reason=reason,
        )
        return self.get_status()

    def stop(
        self,
        *,
        reason: Optional[str] = None,
        requested_by: str = "system",
    ) -> Dict[str, Any]:
        return self.set_stopped(reason=reason, requested_by=requested_by)

    def get_status(self) -> Dict[str, Any]:
        flags = self.node_state_store.get_runtime_flags()
        control = self.node_state_store.get_control_state()

        if flags.get("is_running"):
            status = "running"
        elif flags.get("is_paused"):
            status = "paused"
        elif flags.get("is_stopped"):
            status = "stopped"
        else:
            status = "unknown"

        return {
            "node_id": self.node_id,
            "workspace_id": self.workspace_id,
            "status": status,
            "is_running": bool(flags.get("is_running", False)),
            "is_paused": bool(flags.get("is_paused", False)),
            "is_stopped": bool(flags.get("is_stopped", False)),
            "pause_reason": flags.get("pause_reason"),
            "stop_reason": flags.get("stop_reason"),
            "last_command": control.get("command"),
            "last_command_requested_by": control.get("requested_by"),
            "last_command_reason": control.get("reason"),
            "updated_at": flags.get("updated_at") or utc_now_iso(),
        }

    def create_queue_item(
        self,
        *,
        workflow_id: str,
        operator_id: str,
        department_key: str,
        payload: Dict[str, Any],
    ) -> QueueItem:
        now = utc_now_iso()

        return QueueItem(
            id=f"queue_{uuid.uuid4().hex}",
            workflow_id=workflow_id,
            operator_id=operator_id,
            department_key=department_key,
            status=QueueItemStatus.QUEUED.value,
            payload=payload,
            run_id=None,
            created_at=now,
            updated_at=now,
            started_at=None,
            completed_at=None,
            failure_reason=None,
            workspace_id=self.workspace_id,
        )