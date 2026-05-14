from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.modules.workflow_capsules.architect import (
    WorkflowArchitectProviderOrchestrator,
)


router = APIRouter(prefix="/api/workflow-architect", tags=["workflow-architect"])


class WorkflowArchitectBuildReviewRequest(BaseModel):
    workflow_goal: str = Field(..., min_length=1)
    provider: str = "mock"
    model: Optional[str] = None

    user_steps: List[Dict[str, Any]] = Field(default_factory=list)
    business_context: Dict[str, Any] = Field(default_factory=dict)

    connected_credentials: List[str] = Field(default_factory=list)
    missing_credentials: List[str] = Field(default_factory=list)
    must_not_do: List[str] = Field(default_factory=list)

    inputs: Dict[str, Any] = Field(default_factory=dict)


@router.post("/build-review")
def build_review(payload: WorkflowArchitectBuildReviewRequest) -> Dict[str, Any]:
    """
    Build a workflow proposal through the selected provider adapter and return
    a dry-run-only review payload.

    MVP default provider is "mock". Real provider adapters remain explicit
    future integrations and currently fail closed unless implemented.
    """

    adapter = WorkflowArchitectProviderOrchestrator.adapter_for(
        payload.provider,
        payload.model,
    )

    result = WorkflowArchitectProviderOrchestrator(adapter=adapter).build_and_review(
        workflow_goal=payload.workflow_goal,
        user_steps=payload.user_steps,
        business_context=payload.business_context,
        connected_credentials=payload.connected_credentials,
        missing_credentials=payload.missing_credentials,
        must_not_do=payload.must_not_do,
        inputs=payload.inputs,
    )

    return result.to_dict()


@router.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "workflow_architect",
        "default_provider": "mock",
        "live_send_enabled": False,
        "dry_run_first": True,
    }
