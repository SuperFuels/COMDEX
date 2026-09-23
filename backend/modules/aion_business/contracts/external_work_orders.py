from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


ExternalWorkOrderStatus = Literal[
    "queued",
    "dispatched",
    "in_progress",
    "completed",
    "failed",
    "escalated",
]


class ExternalWorkOrderRecord(BaseModel):
    id: str
    workspace_id: str
    parent_task_id: Optional[str] = None

    capability: str
    objective: str

    specialist_id: Optional[str] = None
    specialist_provider: Optional[str] = None

    status: ExternalWorkOrderStatus = "queued"
    priority: str = "medium"

    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    completed_at: Optional[str] = None