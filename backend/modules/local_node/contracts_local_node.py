from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
import json
import uuid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class DeploymentMode(str, Enum):
    LOCAL_FIRST = "local_first"
    HYBRID = "hybrid"
    CLOUD = "cloud"


class NodeLifecycleState(str, Enum):
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    PAUSED = "paused"
    STOPPED = "stopped"
    OFFLINE = "offline"
    ERROR = "error"


class QueueItemStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ControlCommand(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    CANCEL_RUN = "cancel_run"


@dataclass(slots=True)
class LocalNodeConfig:
    node_id: str
    workspace_id: str
    deployment_mode: DeploymentMode = DeploymentMode.LOCAL_FIRST
    base_dir: str = ".runtime/local_node"
    heartbeat_interval_seconds: int = 10
    max_concurrent_runs: int = 1

    @property
    def base_path(self) -> Path:
        return Path(self.base_dir)


@dataclass(slots=True)
class LocalNodeState:
    node_id: str
    workspace_id: str
    deployment_mode: str
    lifecycle_state: str = NodeLifecycleState.STARTING.value
    last_heartbeat_at: Optional[str] = None
    pause_requested: bool = False
    stop_requested: bool = False
    started_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalNodeState":
        return cls(**data)


@dataclass(slots=True)
class QueueItem:
    id: str
    workspace_id: str
    workflow_id: str
    operator_id: str
    department_key: str
    payload: Dict[str, Any]
    status: str = QueueItemStatus.QUEUED.value
    run_id: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None

    @classmethod
    def new(
        cls,
        *,
        workspace_id: str,
        workflow_id: str,
        operator_id: str,
        department_key: str,
        payload: Dict[str, Any],
    ) -> "QueueItem":
        return cls(
            id=f"queue_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            operator_id=operator_id,
            department_key=department_key,
            payload=payload,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueItem":
        return cls(**data)


@dataclass(slots=True)
class ApprovalRecord:
    id: str
    workspace_id: str
    run_id: str
    operator_id: str
    department_key: str
    title: str
    summary: str
    payload: Dict[str, Any]
    status: str = ApprovalStatus.PENDING.value
    queue_item_id: Optional[str] = None
    requested_at: str = field(default_factory=utc_now_iso)
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None

    @classmethod
    def new(
        cls,
        *,
        workspace_id: str,
        run_id: str,
        operator_id: str,
        department_key: str,
        title: str,
        summary: str,
        payload: Dict[str, Any],
        queue_item_id: Optional[str] = None,
    ) -> "ApprovalRecord":
        return cls(
            id=f"approval_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            run_id=run_id,
            operator_id=operator_id,
            department_key=department_key,
            title=title,
            summary=summary,
            payload=payload,
            queue_item_id=queue_item_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRecord":
        return cls(**data)


@dataclass(slots=True)
class AuditEvent:
    id: str
    node_id: str
    workspace_id: str
    event_type: str
    level: str
    message: str
    payload: Dict[str, Any]
    trace_id: Optional[str] = None
    run_id: Optional[str] = None
    queue_item_id: Optional[str] = None
    approval_id: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def new(
        cls,
        *,
        node_id: str,
        workspace_id: str,
        event_type: str,
        level: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
        queue_item_id: Optional[str] = None,
        approval_id: Optional[str] = None,
    ) -> "AuditEvent":
        return cls(
            id=f"audit_{uuid.uuid4().hex[:12]}",
            node_id=node_id,
            workspace_id=workspace_id,
            event_type=event_type,
            level=level,
            message=message,
            payload=payload or {},
            trace_id=trace_id,
            run_id=run_id,
            queue_item_id=queue_item_id,
            approval_id=approval_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        return cls(**data)


@dataclass(slots=True)
class NodeHealthSnapshot:
    node_id: str
    workspace_id: str
    lifecycle_state: str
    deployment_mode: str
    queue_depth: int
    running_count: int
    pending_approvals: int
    last_heartbeat_at: str
    pause_requested: bool
    stop_requested: bool
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)