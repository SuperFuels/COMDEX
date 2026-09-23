from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.modules.business_runtime.bootstrap_marketing_v1 import bootstrap_marketing_v1
from backend.modules.business_runtime.runtime_singletons import (
    get_approval_runtime,
    get_operator_registry,
    get_workflow_repository,
    get_workflow_runtime,
)

router = APIRouter(prefix="/api/business-runtime", tags=["business-runtime"])


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    return value


class LaunchRunRequest(BaseModel):
    workflow_id: str
    trigger_kind: str = "manual"
    context: Dict[str, Any] = Field(default_factory=dict)


class ResolveApprovalRequest(BaseModel):
    approve: bool
    resolved_by: str
    resolution_note: Optional[str] = None


@router.post("/bootstrap/marketing-v1")
def bootstrap_marketing():
    result = bootstrap_marketing_v1(
        workflow_repository=get_workflow_repository(),
        operator_registry=get_operator_registry(),
    )
    return {"ok": True, **_serialize(result)}


@router.post("/runs/launch")
def launch_run(payload: LaunchRunRequest):
    repo = get_workflow_repository()
    runtime = get_workflow_runtime()

    wf = repo.get_workflow_definition(payload.workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    run = runtime.create_run(
        workflow=wf,
        trigger_kind=payload.trigger_kind,
        initial_context=payload.context,
    )
    run = runtime.execute_run(wf, run)
    return {"ok": True, "run": _serialize(run)}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    repo = get_workflow_repository()
    row = repo.get_workflow_run(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"ok": True, "item": _serialize(row)}


@router.get("/runs")
def list_runs(
    department_key: Optional[str] = Query(default=None),
    operator_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
):
    repo = get_workflow_repository()
    items = repo.list_workflow_runs(
        department_key=department_key,
        operator_id=operator_id,
        limit=limit,
    )
    return {"ok": True, "items": _serialize(items)}


@router.get("/approvals")
def list_approvals(
    status: Optional[str] = Query(default=None),
    department_key: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    runtime = get_approval_runtime()
    items = runtime.list(
        status=status,
        department_key=department_key,
        limit=limit,
    )
    return {"ok": True, "items": _serialize(items)}


@router.post("/approvals/{approval_id}/resolve")
def resolve_approval(approval_id: str, payload: ResolveApprovalRequest):
    approval_runtime = get_approval_runtime()
    workflow_runtime = get_workflow_runtime()
    repo = get_workflow_repository()

    approval = approval_runtime.get(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approval = approval_runtime.resolve(
        approval_id=approval_id,
        approve=payload.approve,
        resolved_by=payload.resolved_by,
        note=payload.resolution_note,
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    row = repo.get_workflow_run(approval["workflow_run_id"])
    if not row:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    run = workflow_runtime.hydrate_run(row)
    wf = repo.get_workflow_definition(run.workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    run = workflow_runtime.resume_after_approval(
        workflow=wf,
        run=run,
        approved=payload.approve,
    )

    return {
        "ok": True,
        "approval": _serialize(approval),
        "run": _serialize(run),
    }