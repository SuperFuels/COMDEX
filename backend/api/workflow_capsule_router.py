from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.modules.workflow_capsules.approval.workflow_capsule_approval_store import (
    WorkflowCapsuleApprovalStore,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    WorkflowCapsuleRunner,
)
from backend.modules.workflow_capsules.canvas.canvas_workflow_compiler import (
    CanvasWorkflowCompiler,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    WorkflowCapsuleRepository,
)
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    WorkflowGlyphRegistry,
)
from backend.modules.workflow_capsules.orchestration.workflow_intent_resolver import (
    WorkflowIntentResolver,
)


router = APIRouter(prefix="/api/workflow-capsules", tags=["workflow-capsules"])


class WorkflowRunDryRequest(BaseModel):
    value: str = "WG-001"
    inputs: Dict[str, Any] = Field(default_factory=dict)
    available_vault_requirements: List[str] = Field(default_factory=list)
    cau_state: Dict[str, Any] = Field(default_factory=lambda: {
        "allow_learn": False,
        "adr_active": False,
        "deny_reason": "api_run_dry_default_no_learning",
    })
    extra: Dict[str, Any] = Field(default_factory=dict)
    create_approval: bool = True


class CanvasCompileSaveRequest(BaseModel):
    canvas: Dict[str, Any]
    scope: str = "workspace"
    workspace_id: Optional[str] = "default_workspace"
    overwrite: bool = True
    rebuild_registry: bool = True


class ApprovalDecisionRequest(BaseModel):
    decided_by: str = "human"
    reason: Optional[str] = None


class ApprovalResumeRequest(BaseModel):
    available_vault_requirements: List[str] = Field(default_factory=list)
    cau_state: Dict[str, Any] = Field(default_factory=lambda: {
        "allow_learn": False,
        "adr_active": False,
        "deny_reason": "api_resume_default_no_learning",
    })
    execution_mode: str = "connector_ready"
    extra: Dict[str, Any] = Field(default_factory=dict)


def get_runner() -> WorkflowCapsuleRunner:
    return WorkflowCapsuleRunner()


def get_intent_resolver() -> WorkflowIntentResolver:
    return WorkflowIntentResolver()


def get_approval_store() -> WorkflowCapsuleApprovalStore:
    return WorkflowCapsuleApprovalStore()


@router.post("/run-dry")
def run_dry(payload: WorkflowRunDryRequest) -> Dict[str, Any]:
    runner = get_runner()
    resolver = get_intent_resolver()

    raw_value = str(payload.value or "").strip()
    resolution = resolver.resolve(raw_value, rebuild_registry=True)
    resolution_payload = resolution.to_dict()

    resolved_value = raw_value
    if resolution.ok and resolution.matched and resolution.canonical_key:
        resolved_value = resolution.canonical_key

    result = runner.run_dry(
        resolved_value,
        inputs=payload.inputs,
        available_vault_requirements=payload.available_vault_requirements,
        cau_state=payload.cau_state,
        extra={
            **payload.extra,
            "source": "workflow_capsule_api",
            "route": "run_dry",
            "raw_value": raw_value,
            "resolved_value": resolved_value,
            "intent_resolution": resolution_payload,
        },
        rebuild_registry=True,
        create_approval=payload.create_approval,
    )

    out = result.to_dict()
    out["intent_resolution"] = resolution_payload
    out["raw_value"] = raw_value
    out["resolved_value"] = resolved_value
    return out


@router.post("/canvas/compile-save")
def compile_save_canvas(payload: CanvasCompileSaveRequest) -> Dict[str, Any]:
    """
    Compile a visual workflow canvas into a WorkflowCapsule and save it.

    Safety:
      - does not execute the workflow,
      - does not create approvals,
      - rejects secret fields,
      - rejects reserved primitive display glyph collisions,
      - stores only vault handles, never raw credentials.
    """

    compiler = CanvasWorkflowCompiler()
    compiled = compiler.compile(payload.canvas)

    if not compiled.ok or compiled.capsule is None:
        return {
            "ok": False,
            "phase": "canvas_compile_save",
            "compiled": compiled.to_dict(),
            "errors": list(compiled.errors),
            "warnings": list(compiled.warnings),
        }

    scope = str(payload.scope or "workspace").strip().lower()
    if scope not in {"core", "workspace"}:
        raise HTTPException(status_code=400, detail="scope must be 'core' or 'workspace'")

    if scope == "workspace" and not payload.workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required for workspace scope")

    repo = WorkflowCapsuleRepository()
    saved = repo.save(
        compiled.capsule,
        scope=scope,
        workspace_id=payload.workspace_id,
        overwrite=payload.overwrite,
    )

    registry_result: Dict[str, Any] = {}
    if payload.rebuild_registry:
        registry = WorkflowGlyphRegistry(repository=repo)
        registry_result = registry.rebuild_and_save()

    return {
        "ok": bool(saved.get("ok")),
        "phase": "canvas_compile_save",
        "canonical_key": compiled.capsule.canonical_key,
        "display_name": compiled.capsule.display_name,
        "display_glyph": compiled.capsule.display_glyph,
        "checksum": compiled.capsule.meta.get("checksum"),
        "scope": scope,
        "workspace_id": payload.workspace_id,
        "path": saved.get("path"),
        "saved": saved,
        "registry": registry_result,
        "compiled_metadata": compiled.metadata,
        "warnings": list(compiled.warnings),
        "executed": False,
    }


@router.get("/approvals")
def list_approvals(
    status: Optional[str] = Query(default=None),
    canonical_key: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> Dict[str, Any]:
    store = get_approval_store()
    items = store.list(status=status, canonical_key=canonical_key, limit=limit)
    return {
        "ok": True,
        "items": items,
        "count": len(items),
    }


@router.get("/approvals/{approval_id}")
def get_approval(approval_id: str) -> Dict[str, Any]:
    store = get_approval_store()
    item = store.get(approval_id)
    if not item:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {
        "ok": True,
        "item": item,
    }


@router.post("/approvals/{approval_id}/approve")
def approve_approval(approval_id: str, payload: ApprovalDecisionRequest) -> Dict[str, Any]:
    runner = get_runner()
    result = runner.approve(
        approval_id,
        decided_by=payload.decided_by,
        reason=payload.reason,
    )

    if not result.get("ok"):
        if result.get("error") == "approval_not_found":
            raise HTTPException(status_code=404, detail="Approval not found")
        raise HTTPException(status_code=400, detail=result)

    return result


@router.post("/approvals/{approval_id}/reject")
def reject_approval(approval_id: str, payload: ApprovalDecisionRequest) -> Dict[str, Any]:
    runner = get_runner()
    result = runner.reject(
        approval_id,
        decided_by=payload.decided_by,
        reason=payload.reason,
    )

    if not result.get("ok"):
        if result.get("error") == "approval_not_found":
            raise HTTPException(status_code=404, detail="Approval not found")
        raise HTTPException(status_code=400, detail=result)

    return result


@router.post("/approvals/{approval_id}/resume")
def resume_approval(approval_id: str, payload: ApprovalResumeRequest) -> Dict[str, Any]:
    """
    Guarded resume endpoint.

    Default execution_mode is connector_ready.
    This endpoint MUST NOT live-execute by default.
    """

    runner = get_runner()
    result = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=payload.available_vault_requirements,
        cau_state=payload.cau_state,
        extra={
            **payload.extra,
            "source": "workflow_capsule_api",
            "route": "resume_after_approval",
        },
        rebuild_registry=True,
        execution_mode=payload.execution_mode or "connector_ready",
    )

    if not result.get("ok"):
        error = str(result.get("error") or "")
        if error == "approval_not_found":
            raise HTTPException(status_code=404, detail="Approval not found")
        return result

    return result
