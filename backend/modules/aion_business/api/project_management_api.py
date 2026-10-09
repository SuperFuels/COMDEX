"""Protected desktop API for the Project Management specialist department."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.aion_flow_session_authority import AionFlowSessionAuthority, VerifiedAionFlowSession
from backend.modules.aion_business.runtime.project_management_service import ProjectManagementService


router = APIRouter(prefix="/api/aion/business/project-management", tags=["aion-project-management"])
_authority = AionFlowSessionAuthority()


async def require_session(request: Request) -> VerifiedAionFlowSession:
    try:
        body = await request.body()
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return _authority.verify(method=request.method, target=target, body=body, headers=request.headers)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class ProjectInput(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    outcome: str = Field(min_length=1, max_length=3000)
    project_type: str = Field(default="other", max_length=60)
    owner: str = Field(default="", max_length=160)
    customer: str = Field(default="", max_length=240)
    start_date: str = Field(default="", max_length=40)
    target_date: str = Field(default="", max_length=40)
    currency: str = Field(default="GBP", max_length=8)
    budget_total: str = Field(default="0", max_length=40)


class ActionInput(BaseModel):
    operation: str = Field(min_length=1, max_length=80)
    fields: dict[str, Any] = Field(default_factory=dict)


class QuestionInput(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class AgentTurnInput(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    project_id: str = Field(default="", max_length=120)
    task_id: str = Field(default="", max_length=120)


def service() -> ProjectManagementService:
    return ProjectManagementService()


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


@router.post("/status")
def status(session: VerifiedAionFlowSession = Depends(require_session)) -> dict[str, Any]:
    return {"ok": True, "state": service().load(session.workspace_id)}


@router.post("/projects")
def create_project(payload: ProjectInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict[str, Any]:
    try:
        state = service().create_project(session.workspace_id, payload.model_dump(), actor_id=session.person_id)
    except ValueError as exc:
        raise _http_error(exc) from exc
    return {"ok": True, "state": state}


@router.post("/projects/{project_id}/actions")
def project_action(
    project_id: str,
    payload: ActionInput,
    session: VerifiedAionFlowSession = Depends(require_session),
) -> dict[str, Any]:
    try:
        state = service().apply_action(
            session.workspace_id, project_id, payload.operation, payload.fields, actor_id=session.person_id,
        )
    except (ValueError, LookupError) as exc:
        raise _http_error(exc) from exc
    return {"ok": True, "state": state}


@router.post("/investigate")
def investigate(payload: QuestionInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict[str, Any]:
    return {"ok": True, "investigation": service().investigate(session.workspace_id, payload.question)}


@router.post("/agent-turn")
def agent_turn(payload: AgentTurnInput, session: VerifiedAionFlowSession = Depends(require_session)) -> dict[str, Any]:
    try:
        result = service().agent_turn(
            session.workspace_id, payload.text, project_id=payload.project_id,
            task_id=payload.task_id, actor_id=session.person_id,
        )
    except (ValueError, LookupError) as exc:
        raise _http_error(exc) from exc
    return {"ok": True, **result}
