from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.modules.local_node.contracts_sync import (
    BatchedSyncPayload,
    SyncPullPayload,
)
from backend.modules.local_node.local_node_runtime import LocalNodeRuntime


class LocalSyncRuntime:
    """
    Local sync runtime.

    This now uses the newer sync payload shape directly:
    - queue_items
    - approvals
    - node_health
    - audit_summaries
    - pushed_at
    - ack_token
    """

    def __init__(self, runtime: LocalNodeRuntime) -> None:
        self.runtime = runtime

    def build_sync_payload(self) -> Dict[str, Any]:
        push_payload = self.runtime.build_sync_push_request()

        payload = BatchedSyncPayload(
            node_id=push_payload.get("node_id", ""),
            workspace_id=push_payload.get("workspace_id", ""),
            pushed_at=push_payload.get("pushed_at") or push_payload.get("at") or "",
            queue_items=push_payload.get("queue_items", []),
            approvals=push_payload.get("approvals", []),
            node_health=push_payload.get("node_health"),
            audit_summaries=push_payload.get("audit_summaries", []),
            ack_token=push_payload.get("ack_token"),
        )
        return payload.to_dict()

    def build_pull_payload(
        self,
        *,
        ack_token: Optional[str] = None,
        commands: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        payload = SyncPullPayload(
            ok=True,
            ack_token=ack_token,
            commands=commands or [],
        )
        return payload.to_dict()

    def mark_push_success(self, *, ack_token: Optional[str] = None) -> Dict[str, Any]:
        return self.runtime.mark_sync_push_success(ack_token=ack_token)

    def mark_pull_success(self, *, ack_token: Optional[str] = None) -> Dict[str, Any]:
        return self.runtime.mark_sync_pull_success(ack_token=ack_token)

    def apply_remote_commands(self, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.runtime.apply_remote_commands(commands)

    def sync_once(
        self,
        *,
        mark_push_success: bool = False,
        push_ack_token: Optional[str] = None,
        remote_commands: Optional[List[Dict[str, Any]]] = None,
        mark_pull_success: bool = False,
        pull_ack_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = self.build_sync_payload()

        out: Dict[str, Any] = {
            "ok": True,
            "payload": payload,
        }

        if mark_push_success:
            out["push_result"] = self.mark_push_success(ack_token=push_ack_token)

        if remote_commands:
            out["pull_payload"] = self.build_pull_payload(
                ack_token=pull_ack_token,
                commands=remote_commands,
            )
            out["command_result"] = self.apply_remote_commands(remote_commands)

        if mark_pull_success:
            out["pull_result"] = self.mark_pull_success(ack_token=pull_ack_token)

        return out