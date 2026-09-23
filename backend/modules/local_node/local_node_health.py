from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from backend.modules.local_node.contracts_local_node import utc_now_iso
from backend.modules.local_node.node_state_store import NodeStateStore


@dataclass(slots=True)
class LocalNodeHealthSnapshot:
    node_id: str
    workspace_id: str
    deployment_mode: str
    status: str
    last_heartbeat_at: str
    started_at: Optional[str] = None
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LocalNodeHealth:
    def __init__(
        self,
        *,
        node_id: str,
        workspace_id: str,
        deployment_mode: str,
        node_state_store: NodeStateStore,
    ) -> None:
        self.node_id = node_id
        self.workspace_id = workspace_id
        self.deployment_mode = deployment_mode
        self.node_state_store = node_state_store

        existing = self.node_state_store.get_heartbeat()
        self._started_at = existing.get("started_at") or utc_now_iso()

        if not existing or existing.get("status") == "unknown":
            self.record_heartbeat(status="created")

    def record_heartbeat(
        self,
        *,
        status: str,
        last_error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LocalNodeHealthSnapshot:
        now = utc_now_iso()

        payload = {
            "node_id": self.node_id,
            "workspace_id": self.workspace_id,
            "deployment_mode": self.deployment_mode,
            "status": status,
            "started_at": self._started_at,
            "last_heartbeat_at": now,
            "recorded_at": now,
            "last_error": last_error,
            "metadata": metadata or {},
        }

        self.node_state_store.save_heartbeat(payload)
        return self.snapshot()

    def snapshot(self) -> LocalNodeHealthSnapshot:
        heartbeat = self.node_state_store.get_heartbeat()

        return LocalNodeHealthSnapshot(
            node_id=str(heartbeat.get("node_id") or self.node_id),
            workspace_id=str(heartbeat.get("workspace_id") or self.workspace_id),
            deployment_mode=str(
                heartbeat.get("deployment_mode") or self.deployment_mode
            ),
            status=str(heartbeat.get("status") or "unknown"),
            last_heartbeat_at=str(
                heartbeat.get("last_heartbeat_at")
                or heartbeat.get("recorded_at")
                or utc_now_iso()
            ),
            started_at=heartbeat.get("started_at") or self._started_at,
            last_error=heartbeat.get("last_error"),
            metadata=heartbeat.get("metadata")
            if isinstance(heartbeat.get("metadata"), dict)
            else {},
        )

    def get_status(self) -> Dict[str, Any]:
        return self.snapshot().to_dict()