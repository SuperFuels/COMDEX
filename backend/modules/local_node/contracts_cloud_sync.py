from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from backend.modules.local_node.contracts_local_node import utc_now_iso


@dataclass(slots=True)
class CloudSyncQueueItem:
    id: str
    workflow_id: str
    operator_id: str
    department_key: str
    status: str
    run_id: Optional[str]
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    workspace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CloudSyncApprovalItem:
    id: str
    queue_item_id: Optional[str]
    run_id: Optional[str]
    status: str
    requested_at: str
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None
    workspace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CloudSyncNodeHealth:
    node_id: str
    workspace_id: str
    deployment_mode: str
    status: str
    heartbeat_at: str
    started_at: Optional[str] = None
    queue_depth: int = 0
    running_count: int = 0
    waiting_approval_count: int = 0
    failed_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CloudSyncAuditSummaryItem:
    id: str
    event_type: str
    level: str
    created_at: str
    message: str
    run_id: Optional[str] = None
    queue_item_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CloudSyncPushRequest:
    node_id: str
    workspace_id: str
    pushed_at: str
    queue_items: List[CloudSyncQueueItem] = field(default_factory=list)
    approvals: List[CloudSyncApprovalItem] = field(default_factory=list)
    node_health: Optional[CloudSyncNodeHealth] = None
    audit_summaries: List[CloudSyncAuditSummaryItem] = field(default_factory=list)
    ack_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "workspace_id": self.workspace_id,
            "pushed_at": self.pushed_at,
            "queue_items": [x.to_dict() for x in self.queue_items],
            "approvals": [x.to_dict() for x in self.approvals],
            "node_health": self.node_health.to_dict() if self.node_health else None,
            "audit_summaries": [x.to_dict() for x in self.audit_summaries],
            "ack_token": self.ack_token,
        }


@dataclass(slots=True)
class CloudSyncRemoteCommand:
    id: str
    command_type: str  # pause | resume | cancel_run | resume_approval
    target_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    issued_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CloudSyncPullResponse:
    ok: bool
    pulled_at: str
    ack_token: Optional[str] = None
    commands: List[CloudSyncRemoteCommand] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "pulled_at": self.pulled_at,
            "ack_token": self.ack_token,
            "commands": [x.to_dict() for x in self.commands],
        }