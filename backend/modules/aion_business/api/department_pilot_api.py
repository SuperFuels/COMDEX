"""Runtime API for Central Pilot routing and specialist Department Pilot queues."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.modules.aion_business.contracts.department_pilot import (
    BoardroomAssignmentAction,
    BoardroomAssignmentPackage,
    ContextReference,
    DepartmentPilotWorkEnvelope,
)
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.canonical_business_identity import (
    canonical_business_id,
)
from backend.modules.aion_business.runtime.central_pilot_department_router import (
    CentralPilotDepartmentRouter,
    DepartmentPilotDesignRequiredError,
)
from backend.modules.aion_business.runtime.department_context_assembler import (
    DepartmentContextAssembler,
)
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    approve_assignment_package,
    create_assignment_package,
    create_provenance,
)
from backend.modules.aion_business.runtime.department_pilot_profiles import (
    get_department_pilot_profile,
    list_department_pilot_profiles,
)
from backend.modules.aion_business.runtime.department_pilot_repository import (
    DepartmentPilotConcurrencyError,
    DepartmentPilotRepository,
)
from backend.modules.aion_business.runtime.department_pilot_runtime import (
    DepartmentPilotRuntime,
)


router = APIRouter(
    prefix="/api/aion/business/department-pilots",
    tags=["aion-business-department-pilots"],
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def get_department_pilot_repository() -> DepartmentPilotRepository:
    return DepartmentPilotRepository()


def get_business_container_repository() -> BusinessContainerRepository:
    return BusinessContainerRepository()


def _canonical_workspace(candidate: str) -> str:
    try:
        return canonical_business_id(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _profile_or_404(department_id: str) -> dict[str, Any]:
    profile = get_department_pilot_profile(department_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Unknown Department Pilot: {department_id}")
    return profile


def _load_or_404(
    repository: DepartmentPilotRepository,
    workspace_id: str,
    department_id: str,
    task_id: str,
) -> DepartmentPilotWorkEnvelope:
    try:
        return repository.load(workspace_id, department_id, task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class RouteBoardroomPackageRequest(BaseModel):
    package: BoardroomAssignmentPackage
    routed_at: Optional[str] = None
    routed_by: str = "central_pilot"


class ApproveAndRouteBoardroomPackageRequest(BaseModel):
    package: BoardroomAssignmentPackage
    approval_id: str
    approved_by: str
    approved_at: Optional[str] = None
    approval_notes: Optional[str] = None
    routed_at: Optional[str] = None
    routed_by: str = "central_pilot"


class ApproveBoardroomActionRequest(BaseModel):
    workspace_id: str
    business_id: str
    boardroom_session_id: str
    boardroom_decision_id: str
    package_id: str
    title: str
    objective: str
    department_id: str
    actions: list[BoardroomAssignmentAction]
    context_refs: list[ContextReference] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    approval_id: str
    approved_by: str
    approved_at: Optional[str] = None
    approval_notes: Optional[str] = None


class TaskTransitionRequest(BaseModel):
    to_status: str
    occurred_at: Optional[str] = None
    actor_id: str
    event_id: str
    message: Optional[str] = None
    progress_percent: Optional[int] = Field(default=None, ge=0, le=100)
    data: dict[str, Any] = Field(default_factory=dict)


class ConversationTurnRequest(BaseModel):
    turn_id: str
    role: str
    content: str
    created_at: Optional[str] = None
    actor_id: Optional[str] = None
    tool_call_id: Optional[str] = None


class RetrieveContextRequest(BaseModel):
    retrieved_at: Optional[str] = None
    retrieved_by: str


@router.get("/profiles")
def list_profiles() -> dict[str, Any]:
    profiles = list_department_pilot_profiles()
    return {
        "schema_version": "aion.department_pilot.profile_registry.v1",
        "profiles": profiles,
        "enabled_department_ids": [
            item["department_id"]
            for item in profiles
            if item["activation_state"] == "enabled"
        ],
        "design_required_department_ids": [
            item["department_id"]
            for item in profiles
            if item["activation_state"] == "design_required"
        ],
    }


@router.post("/route")
def route_boardroom_package(request: RouteBoardroomPackageRequest) -> dict[str, Any]:
    return _route_approved_package(
        request.package,
        routed_at=request.routed_at or _now(),
        routed_by=request.routed_by,
    )


def _route_approved_package(
    package: BoardroomAssignmentPackage,
    *,
    routed_at: str,
    routed_by: str,
) -> dict[str, Any]:
    workspace_id = _canonical_workspace(package.workspace_id)
    business_id = _canonical_workspace(package.business_id)
    if package.workspace_id != workspace_id or package.business_id != business_id:
        raise HTTPException(
            status_code=409,
            detail="Boardroom package must use the canonical business identity.",
        )
    if workspace_id != business_id:
        raise HTTPException(status_code=409, detail="Package workspace/business mismatch.")

    repository = get_department_pilot_repository()
    runtime = DepartmentPilotRuntime(repository)
    central_router = CentralPilotDepartmentRouter(repository, runtime)
    try:
        envelopes = central_router.route_approved_package(
            package,
            routed_at=routed_at,
            routed_by=routed_by,
        )
    except DepartmentPilotDesignRequiredError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "department_pilot_design_required",
                "department_id": exc.department_id,
                "design_topics": exc.design_topics,
            },
        ) from exc
    except (ValueError, FileExistsError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "ok": True,
        "routing_state": "routed_to_specialist_pilot",
        "workspace_id": workspace_id,
        "department_id": package.department_id,
        "package_id": package.package_id,
        "package_hash": package.package_hash,
        "task_count": len(envelopes),
        "tasks": [item.model_dump(mode="json") for item in envelopes],
    }


@router.post("/approve-and-route")
def approve_and_route_boardroom_package(
    request: ApproveAndRouteBoardroomPackageRequest,
) -> dict[str, Any]:
    """Approve a draft package and deliver it without a second routing action."""

    if request.package.status not in {"draft", "awaiting_approval"}:
        raise HTTPException(
            status_code=409,
            detail="Only a draft or awaiting-approval package may use approve-and-route.",
        )
    if request.package.approval is not None:
        raise HTTPException(status_code=409, detail="Package already contains an approval.")

    approved_at = request.approved_at or _now()
    try:
        approved_package = approve_assignment_package(
            request.package,
            approval_id=request.approval_id,
            approved_by=request.approved_by,
            approved_at=approved_at,
            notes=request.approval_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    result = _route_approved_package(
        approved_package,
        routed_at=request.routed_at or approved_at,
        routed_by=request.routed_by,
    )
    result["approval_state"] = "approved_and_routed"
    result["approved_package"] = approved_package.model_dump(mode="json")
    return result


@router.post("/approve-boardroom-action")
def approve_boardroom_action(request: ApproveBoardroomActionRequest) -> dict[str, Any]:
    """Canonical Boardroom producer: build, approve and route explicit actions."""

    workspace_id = _canonical_workspace(request.workspace_id)
    business_id = _canonical_workspace(request.business_id)
    if request.workspace_id != workspace_id or request.business_id != business_id:
        raise HTTPException(
            status_code=409,
            detail="Boardroom action must use the canonical business identity.",
        )
    if workspace_id != business_id:
        raise HTTPException(status_code=409, detail="Boardroom workspace/business mismatch.")
    if not request.actions:
        raise HTTPException(status_code=409, detail="Boardroom action list cannot be empty.")
    if any(action.department_id != request.department_id for action in request.actions):
        raise HTTPException(status_code=409, detail="Boardroom action department mismatch.")

    approved_at = request.approved_at or _now()
    try:
        draft = create_assignment_package(
            package_id=request.package_id,
            workspace_id=workspace_id,
            business_id=business_id,
            boardroom_session_id=request.boardroom_session_id,
            boardroom_decision_id=request.boardroom_decision_id,
            title=request.title,
            objective=request.objective,
            department_id=request.department_id,
            actions=request.actions,
            context_refs=request.context_refs,
            constraints=request.constraints,
            provenance=create_provenance(
                created_by="aion_boardroom",
                created_at=approved_at,
                source_system="aion_boardroom",
                source_record_id=request.boardroom_decision_id,
                correlation_id=request.boardroom_session_id,
            ),
        )
        approved = approve_assignment_package(
            draft,
            approval_id=request.approval_id,
            approved_by=request.approved_by,
            approved_at=approved_at,
            notes=request.approval_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    result = _route_approved_package(
        approved,
        routed_at=approved_at,
        routed_by="central_pilot",
    )
    result["approval_state"] = "boardroom_action_approved_and_routed"
    result["approved_package"] = approved.model_dump(mode="json")
    return result


@router.get("/monitor/{workspace_id}")
def monitor_workspace(
    workspace_id: str,
    status: list[str] = Query(default=[]),
) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    repository = get_department_pilot_repository()
    envelopes = repository.list_for_workspace(
        workspace_id,
        statuses=status or None,  # type: ignore[arg-type]
    )
    counts: dict[str, int] = {}
    for envelope in envelopes:
        counts[envelope.task.status] = counts.get(envelope.task.status, 0) + 1
    return {
        "schema_version": "aion.central_pilot.department_monitor.v1",
        "workspace_id": workspace_id,
        "task_count": len(envelopes),
        "status_counts": counts,
        "tasks": [item.model_dump(mode="json") for item in envelopes],
    }


@router.get("/{workspace_id}/{department_id}")
def list_department_queue(
    workspace_id: str,
    department_id: str,
    status: list[str] = Query(default=[]),
) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    profile = _profile_or_404(department_id)
    envelopes = get_department_pilot_repository().list_for_department(
        workspace_id,
        department_id,  # type: ignore[arg-type]
        statuses=status or None,  # type: ignore[arg-type]
    )
    return {
        "workspace_id": workspace_id,
        "department_id": department_id,
        "profile": {"department_id": department_id, **profile},
        "task_count": len(envelopes),
        "tasks": [item.model_dump(mode="json") for item in envelopes],
    }


@router.get("/{workspace_id}/{department_id}/{task_id}")
def get_department_task(
    workspace_id: str,
    department_id: str,
    task_id: str,
) -> DepartmentPilotWorkEnvelope:
    workspace_id = _canonical_workspace(workspace_id)
    _profile_or_404(department_id)
    return _load_or_404(
        get_department_pilot_repository(), workspace_id, department_id, task_id
    )


@router.post("/{workspace_id}/{department_id}/{task_id}/transition")
def transition_department_task(
    workspace_id: str,
    department_id: str,
    task_id: str,
    request: TaskTransitionRequest,
) -> DepartmentPilotWorkEnvelope:
    workspace_id = _canonical_workspace(workspace_id)
    profile = _profile_or_404(department_id)
    if profile.get("activation_state") != "enabled":
        raise HTTPException(status_code=409, detail="Department Pilot design is not approved.")
    runtime = DepartmentPilotRuntime(get_department_pilot_repository())
    try:
        return runtime.transition(
            workspace_id=workspace_id,
            department_id=department_id,
            task_id=task_id,
            to_status=request.to_status,
            occurred_at=request.occurred_at or _now(),
            actor_id=request.actor_id,
            event_id=request.event_id,
            message=request.message,
            progress_percent=request.progress_percent,
            data=request.data,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, DepartmentPilotConcurrencyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{workspace_id}/{department_id}/{task_id}/conversation")
def append_department_conversation(
    workspace_id: str,
    department_id: str,
    task_id: str,
    request: ConversationTurnRequest,
) -> DepartmentPilotWorkEnvelope:
    workspace_id = _canonical_workspace(workspace_id)
    profile = _profile_or_404(department_id)
    if profile.get("activation_state") != "enabled":
        raise HTTPException(status_code=409, detail="Department Pilot design is not approved.")
    runtime = DepartmentPilotRuntime(get_department_pilot_repository())
    try:
        return runtime.append_conversation_turn(
            workspace_id=workspace_id,
            department_id=department_id,
            task_id=task_id,
            turn_id=request.turn_id,
            role=request.role,
            content=request.content,
            created_at=request.created_at or _now(),
            actor_id=request.actor_id,
            tool_call_id=request.tool_call_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, DepartmentPilotConcurrencyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{workspace_id}/{department_id}/{task_id}/retrieve-context")
def retrieve_department_context(
    workspace_id: str,
    department_id: str,
    task_id: str,
    request: RetrieveContextRequest,
) -> DepartmentPilotWorkEnvelope:
    workspace_id = _canonical_workspace(workspace_id)
    profile = _profile_or_404(department_id)
    if profile.get("activation_state") != "enabled":
        raise HTTPException(status_code=409, detail="Department Pilot design is not approved.")
    repository = get_department_pilot_repository()
    task = _load_or_404(repository, workspace_id, department_id, task_id)
    assembler = DepartmentContextAssembler(get_business_container_repository())
    evidence = assembler.retrieve_for_task(
        task.task,
        retrieved_at=request.retrieved_at or _now(),
        retrieved_by=request.retrieved_by,
    )
    try:
        return DepartmentPilotRuntime(repository).attach_retrieved_evidence(
            workspace_id=workspace_id,
            department_id=department_id,
            task_id=task_id,
            evidence=evidence,
        )
    except DepartmentPilotConcurrencyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
