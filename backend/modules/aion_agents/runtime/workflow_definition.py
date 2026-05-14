from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


WorkflowStepKind = Literal[
    "start",
    "draft_content",
    "approval_checkpoint",
    "send_email",
    "post_social",
    "update_crm",
    "create_document",
    "wait",
    "complete",
]


class WorkflowStepDefinition(BaseModel):
    id: str
    name: str
    kind: WorkflowStepKind
    config: Dict[str, Any] = Field(default_factory=dict)
    next_step_id: Optional[str] = None
    on_success_step_id: Optional[str] = None
    on_failure_step_id: Optional[str] = None
    requires_approval: bool = False


class WorkflowDefinition(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    version: int = 1
    status: Literal["draft", "active", "archived"] = "draft"
    execution_mode: Literal["draft_only", "draft_and_approval", "autonomous"] = (
        "draft_and_approval"
    )
    department_key: Optional[str] = None
    agent_id: Optional[str] = None
    trigger_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    steps: List[WorkflowStepDefinition] = Field(default_factory=list)

    def get_step(self, step_id: str) -> Optional[WorkflowStepDefinition]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_first_step(self) -> Optional[WorkflowStepDefinition]:
        if not self.steps:
            return None
        return self.steps[0]