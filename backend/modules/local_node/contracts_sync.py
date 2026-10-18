from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from backend.modules.local_node.contracts_local_node import utc_now_iso


@dataclass(slots=True)
class SyncCursor:
    last_push_at: Optional[str] = None
    last_pull_at: Optional[str] = None
    last_ack_token: Optional[str] = None
    last_success_at: Optional[str] = None
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SyncEnvelope:
    node_id: str
    workspace_id: str
    kind: str
    created_at: str = field(default_factory=utc_now_iso)
    payload: Dict[str, Any] = field(default_factory=dict)
    ack_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SyncQueueItem:
    id: str
    workflow_id: str
    operator_id: str
    department_key: str
    status: str
    run_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    workspace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SyncApprovalItem:
    id: str
    status: str
    requested_at: str
    workflow_run_id: Optional[str] = None
    queue_item_id: Optional[str] = None
    run_id: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None
    workspace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SyncAuditSummaryItem:
    id: str
    event_type: str
    level: str
    message: str
    created_at: str
    trace_id: Optional[str] = None
    run_id: Optional[str] = None
    queue_item_id: Optional[str] = None
    approval_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SyncNodeHealth:
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
class SyncRemoteCommand:
    id: str
    command_type: str
    target_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    issued_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BatchedSyncPayload:
    node_id: str
    workspace_id: str
    pushed_at: str = field(default_factory=utc_now_iso)
    queue_items: List[Dict[str, Any]] = field(default_factory=list)
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    node_health: Optional[Dict[str, Any]] = None
    audit_summaries: List[Dict[str, Any]] = field(default_factory=list)
    ack_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "workspace_id": self.workspace_id,
            "pushed_at": self.pushed_at,
            "queue_items": self.queue_items,
            "approvals": self.approvals,
            "node_health": self.node_health,
            "audit_summaries": self.audit_summaries,
            "ack_token": self.ack_token,
        }


@dataclass(slots=True)
class SyncPullPayload:
    ok: bool = True
    pulled_at: str = field(default_factory=utc_now_iso)
    ack_token: Optional[str] = None
    commands: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "pulled_at": self.pulled_at,
            "ack_token": self.ack_token,
            "commands": self.commands,
        }