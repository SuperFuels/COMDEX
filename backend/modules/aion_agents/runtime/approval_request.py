from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


ApprovalStatus = Literal["pending", "approved", "rejected", "cancelled"]


class ApprovalRequest(BaseModel):
    id: str
    workspace_id: str
    workflow_run_id: str
    workflow_id: str
    agent_id: Optional[str] = None
    department_key: Optional[str] = None
    title: str
    summary: Optional[str] = None
    approval_class: Literal["draft_review", "send_review", "publish_review", "critical"] = (
        "draft_review"
    )
    status: ApprovalStatus = "pending"
    requested_action: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    requested_at: str
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None