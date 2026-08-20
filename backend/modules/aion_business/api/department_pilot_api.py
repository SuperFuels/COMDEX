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
    canonical_contract_hash,
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
    create_context_reference,
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
from backend.modules.aion_business.runtime.finance_pilot_execution_service import (
    FinancePilotExecutionService,
)
from backend.modules.aion_business.runtime.finance_forecasting_service import (
    FinanceForecastingService,
)
from backend.modules.aion_business.runtime.finance_reconciliation_service import (
    FinanceReconciliationService,
)
from backend.modules.aion_business.runtime.finance_controlled_action_service import (
    FinanceControlledActionService,
)
from backend.modules.aion_business.runtime.finance_recurring_work_service import (
    FinanceRecurringWorkService,
)
from backend.modules.aion_business.runtime.department_pilot_recovery_service import (
    DepartmentPilotRecoveryService,
)
from backend.modules.aion_business.runtime.department_discovery_planner_service import (
    DepartmentDiscoveryPlannerService,
)
from backend.modules.aion_business.runtime.finance_pilot_conversation_service import (
    FinancePilotConversationService,
)
from backend.modules.aion_business.runtime.finance_security_policy import (
    get_finance_security_policy,
)
from backend.modules.aion_business.runtime.finance_ledger_service import (
    FinanceLedgerService,
)
from backend.modules.aion_business.runtime.finance_transaction_reconciliation_service import (
    FinanceTransactionReconciliationService,
)
from backend.modules.aion_business.runtime.finance_director_service import (
    FinanceDirectorService,
)
from backend.modules.aion_business.runtime.xero_reconciliation_handoff_service import (
    XeroReconciliationHandoffService,
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


@router.get("/{workspace_id}/finance/security-policy")
def get_finance_permission_and_sensitive_data_policy(workspace_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "policy": get_finance_security_policy(),
    }


def get_finance_pilot_conversation_service() -> FinancePilotConversationService:
    return FinancePilotConversationService(
        container_repository=get_business_container_repository()
    )


def get_department_discovery_planner_service() -> DepartmentDiscoveryPlannerService:
    return DepartmentDiscoveryPlannerService(
        container_repository=get_business_container_repository()
    )


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


_COMMON_BOARDROOM_CONTEXT_KINDS = (
    "business_identity",
    "business_map",
    "department_intelligence",
)

_DEPARTMENT_BOARDROOM_CONTEXT_KINDS = {
    "finance": ("business_financial_model", "business_operating_model"),
}

_CONTEXT_VERIFICATION_STATES = {
    "business_identity": "founder_supplied",
    "business_map": "unverified",
    "department_intelligence": "unverified",
    "business_financial_model": "unverified",
    "business_operating_model": "founder_supplied",
}


def _bind_current_boardroom_context(
    workspace_id: str,
    department_id: str,
) -> list[ContextReference]:
    """Hash-bind the canonical context that exists when the founder approves work."""

    repository = get_business_container_repository()
    kinds = (
        *_COMMON_BOARDROOM_CONTEXT_KINDS,
        *_DEPARTMENT_BOARDROOM_CONTEXT_KINDS.get(department_id, ()),
    )
    references: list[ContextReference] = []
    for kind in kinds:
        payload = repository.load_optional_dict(workspace_id, kind)  # type: ignore[arg-type]
        if payload is None:
            continue
        revision = payload.get("revision")
        references.append(
            create_context_reference(
                reference_id=f"boardroom:{department_id}:{kind}:r{revision or 1}",
                workspace_id=workspace_id,
                container_kind=kind,
                container_id=str(payload.get("id") or f"{workspace_id}.{kind}"),
                revision=revision if isinstance(revision, int) else None,
                content_hash=canonical_contract_hash(payload),
                verification_state=_CONTEXT_VERIFICATION_STATES.get(kind, "unverified"),
                summary=f"{kind.replace('_', ' ').title()} bound at Boardroom approval.",
            )
        )
    return references


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


class ExecuteFinanceTaskRequest(BaseModel):
    executed_at: Optional[str] = None
    actor_id: str = "finance_pilot"


class FinanceConversationRequest(BaseModel):
    user_text: str = Field(..., min_length=1, max_length=4000)
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    created_at: Optional[str] = None


class DepartmentDiscoveryQuestionRequest(BaseModel):
    resolved_field_keys: list[str] = Field(default_factory=list, max_length=200)
    skipped_field_keys: list[str] = Field(default_factory=list, max_length=200)
    recent_questions: list[str] = Field(default_factory=list, max_length=50)
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None


class FinanceScenarioRequest(BaseModel):
    scenario_id: Optional[str] = None
    scenario_name: str = Field(default="Finance planning scenario", min_length=1, max_length=160)
    forecast_months: int = Field(default=12, ge=1, le=36)
    annual_revenue_growth_percent: float = 0
    revenue_change_percent: float = 0
    price_change_percent: float = 0
    volume_change_percent: float = 0
    direct_cost_change_percent: float = 0
    overhead_change_percent: float = 0
    monthly_hiring_cost: float = Field(default=0, ge=0)
    one_off_stock_purchase: float = Field(default=0, ge=0)
    stock_purchase_month: int = Field(default=1, ge=1, le=36)
    opening_cash: Optional[float] = None
    minimum_cash_reserve: float = Field(default=0, ge=0)
    sensitivity_percent: float = Field(default=10, ge=0, le=100)
    created_at: Optional[str] = None
    created_by: str = "finance_pilot"


class FinanceReconciliationRequest(BaseModel):
    artifact_periods: dict[str, dict[str, Optional[str]]] = Field(default_factory=dict)
    tolerance_percent: float = Field(default=1, ge=0, le=100)
    created_at: Optional[str] = None
    created_by: str = "finance_pilot"


class FinanceReconciliationReviewRequest(BaseModel):
    decision: str
    reviewed_by: str
    notes: Optional[str] = None
    reviewed_at: Optional[str] = None


class FinanceLedgerBuildRequest(BaseModel):
    created_at: Optional[str] = None
    created_by: str = "finance_pilot"


class FinanceTransactionReconciliationRequest(BaseModel):
    amount_tolerance_percent: float = Field(default=1, ge=0, le=100)
    date_window_days: int = Field(default=7, ge=0, le=90)
    created_at: Optional[str] = None
    created_by: str = "finance_pilot"
    classify_unmatched: bool = True
    classification_limit: int = Field(default=25, ge=0, le=50)
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None


class FinanceTransactionMatchReviewRequest(BaseModel):
    decision: str
    reviewed_by: str
    notes: Optional[str] = None
    reviewed_at: Optional[str] = None


class FinanceCounterpartyClassificationReviewRequest(BaseModel):
    decision: str
    reviewed_by: str
    selected_account: Optional[dict[str, Any]] = None
    notes: Optional[str] = None
    reviewed_at: Optional[str] = None


class XeroReconciliationHandoffPrepareRequest(BaseModel):
    prepared_by: str = "finance_pilot"
    prepared_at: Optional[str] = None


class XeroReconciliationHandoffDecisionRequest(BaseModel):
    approved: bool
    decided_by: str
    decided_payload_hash: Optional[str] = None
    reason: Optional[str] = None
    decided_at: Optional[str] = None


class XeroReconciliationHandoffExecuteRequest(BaseModel):
    attempted_by: str
    attempted_at: Optional[str] = None


class FinanceDirectorRefreshRequest(BaseModel):
    minimum_cash_reserve: Optional[float] = Field(default=None, ge=0)
    created_at: Optional[str] = None
    created_by: str = "finance_pilot"


class FinanceControlledProposalRequest(BaseModel):
    tool_call_id: str
    tool_name: str
    provider: str
    payload: dict[str, Any]
    rationale: str = Field(..., min_length=1, max_length=2000)
    proposed_by: str = "finance_pilot"
    proposed_at: Optional[str] = None


class FinanceControlledProposalDecisionRequest(BaseModel):
    approval_id: str
    approved: bool
    decided_by: str
    decided_payload_hash: Optional[str] = None
    reason: Optional[str] = None
    decided_at: Optional[str] = None


class FinanceRecurringScheduleRequest(BaseModel):
    schedule_id: str = Field(..., min_length=1, max_length=120)
    kind: str
    cadence: str
    next_run_at: str
    created_by: str = "finance_pilot"
    minimum_cash_reserve: float = Field(default=0, ge=0)


class FinanceRecurringEnabledRequest(BaseModel):
    enabled: bool


class FinanceRecurringRunRequest(BaseModel):
    run_at: Optional[str] = None
    actor_id: str = "finance_scheduler"


class DepartmentTaskRecoveryRequest(BaseModel):
    actor_id: str
    occurred_at: Optional[str] = None
    reason: Optional[str] = None


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
    context_refs = request.context_refs or _bind_current_boardroom_context(
        workspace_id, request.department_id
    )
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
            context_refs=context_refs,
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
    result["context_binding_state"] = "hash_bound_at_boardroom_approval"
    result["context_reference_count"] = len(context_refs)
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


@router.get("/{workspace_id}/finance/conversation/session")
def get_finance_conversation_session(workspace_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    _profile_or_404("finance")
    session = get_finance_pilot_conversation_service().get_session(workspace_id)
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "department_id": "finance",
        "session": session,
    }


@router.post("/{workspace_id}/{department_id}/discovery/next-question")
def plan_department_discovery_question(
    workspace_id: str,
    department_id: str,
    request: DepartmentDiscoveryQuestionRequest,
) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    _profile_or_404(department_id)
    try:
        return get_department_discovery_planner_service().next_question(
            workspace_id,
            department_id,
            resolved_field_keys=request.resolved_field_keys,
            skipped_field_keys=request.skipped_field_keys,
            recent_questions=request.recent_questions,
            preferred_provider=request.preferred_provider,
            preferred_model=request.preferred_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{workspace_id}/finance/conversation/turn")
def create_finance_conversation_turn(
    workspace_id: str,
    request: FinanceConversationRequest,
) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    profile = _profile_or_404("finance")
    if profile.get("activation_state") != "enabled":
        raise HTTPException(status_code=409, detail="Finance Pilot is not enabled.")
    try:
        return get_finance_pilot_conversation_service().answer(
            workspace_id,
            request.user_text,
            preferred_provider=request.preferred_provider,
            preferred_model=request.preferred_model,
            created_at=request.created_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.post("/{workspace_id}/finance/{task_id}/execute-read-only")
def execute_finance_task_read_only(
    workspace_id: str,
    task_id: str,
    request: ExecuteFinanceTaskRequest,
) -> dict[str, Any]:
    """Run the approved Finance analysis and prepare its Boardroom handback."""

    workspace_id = _canonical_workspace(workspace_id)
    profile = _profile_or_404("finance")
    if profile.get("activation_state") != "enabled":
        raise HTTPException(status_code=409, detail="Finance Pilot is not enabled.")
    service = FinancePilotExecutionService(
        task_repository=get_department_pilot_repository(),
        container_repository=get_business_container_repository(),
    )

    def record_failure(message: str) -> None:
        repository = get_department_pilot_repository()
        try:
            current = repository.load(workspace_id, "finance", task_id)
            if current.task.status not in {"claimed", "running"}:
                return
            DepartmentPilotRuntime(repository).transition(
                workspace_id=workspace_id,
                department_id="finance",
                task_id=task_id,
                to_status="failed",
                occurred_at=request.executed_at or _now(),
                actor_id=request.actor_id,
                event_id=f"{task_id}-failed",
                message=f"Finance analysis failed: {message}",
                progress_percent=None,
                data={"error": message},
            )
        except Exception:
            return

    try:
        envelope, report, pointer = service.execute(
            workspace_id,
            task_id,
            actor_id=request.actor_id,
            executed_at=request.executed_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "finance_pilot_permission_denied", "message": str(exc)},
        ) from exc
    except (ValueError, DepartmentPilotConcurrencyError) as exc:
        record_failure(str(exc))
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        record_failure(str(exc))
        raise HTTPException(
            status_code=500,
            detail={"code": "finance_pilot_execution_failed", "message": str(exc)},
        ) from exc
    return {
        "ok": True,
        "execution_state": "completed_for_boardroom_handback",
        "workspace_id": workspace_id,
        "task_id": task_id,
        "envelope": envelope.model_dump(mode="json"),
        "report": report,
        "file_cabinet_pointer": pointer,
    }


@router.post("/{workspace_id}/finance/scenarios/run")
def run_finance_scenario(
    workspace_id: str,
    request: FinanceScenarioRequest,
) -> dict[str, Any]:
    """Run a read-only scenario without changing historical Finance truth."""

    workspace_id = _canonical_workspace(workspace_id)
    profile = _profile_or_404("finance")
    if profile.get("activation_state") != "enabled":
        raise HTTPException(status_code=409, detail="Finance Pilot is not enabled.")
    payload = request.model_dump(exclude={"scenario_name", "created_at", "created_by"})
    try:
        scenario, pointer = FinanceForecastingService(
            container_repository=get_business_container_repository()
        ).run(
            workspace_id,
            payload,
            scenario_name=request.scenario_name,
            created_by=request.created_by,
            created_at=request.created_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "scenario": scenario,
        "file_cabinet_pointer": pointer,
    }


@router.get("/finance-scenarios")
def list_finance_scenarios(workspace_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        records = FinanceForecastingService(
            container_repository=get_business_container_repository()
        ).list(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "ok": True,
        "workspace_id": workspace_id,
        "scenarios": records,
        "latest_scenario": records[0] if records else None,
    }


@router.post("/{workspace_id}/finance/reconciliations/run")
def run_finance_reconciliation(workspace_id: str, request: FinanceReconciliationRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        record = FinanceReconciliationService(get_business_container_repository()).run(
            workspace_id,
            artifact_periods=request.artifact_periods,
            tolerance=request.tolerance_percent / 100,
            created_at=request.created_at or _now(),
            created_by=request.created_by,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "reconciliation": record}


@router.post("/{workspace_id}/finance/reconciliations/{reconciliation_id}/review")
def review_finance_reconciliation(workspace_id: str, reconciliation_id: str, request: FinanceReconciliationReviewRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        record = FinanceReconciliationService(get_business_container_repository()).review(
            workspace_id, reconciliation_id, decision=request.decision,
            reviewed_by=request.reviewed_by, notes=request.notes,
            reviewed_at=request.reviewed_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "reconciliation": record}


@router.get("/finance-reconciliations")
def list_finance_reconciliations(workspace_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        records = FinanceReconciliationService(get_business_container_repository()).list(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "reconciliations": records, "latest_reconciliation": records[0] if records else None}


@router.post("/finance-ledger-build")
def build_finance_ledger(workspace_id: str, request: FinanceLedgerBuildRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        ledger = FinanceLedgerService(get_business_container_repository()).build(
            workspace_id, created_by=request.created_by, created_at=request.created_at or _now()
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "ledger": ledger, "external_write_performed": False}


@router.get("/finance-ledger")
def get_finance_ledger(workspace_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        ledger = FinanceLedgerService(get_business_container_repository()).latest(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "ledger": ledger}


@router.get("/finance-ledger-records")
def get_finance_ledger_records(workspace_id: str, ledger_id: str, collection: str,
                               limit: int = Query(default=200, ge=1, le=1000),
                               offset: int = Query(default=0, ge=0)) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        records = FinanceLedgerService(get_business_container_repository()).records(
            workspace_id, ledger_id, collection, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "ledger_id": ledger_id,
            "collection": collection, "offset": offset, "count": len(records), "records": records}


@router.post("/finance-transaction-reconciliation-run")
def run_finance_transaction_reconciliation(workspace_id: str,
                                           request: FinanceTransactionReconciliationRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        record = FinanceTransactionReconciliationService(get_business_container_repository()).run(
            workspace_id, created_by=request.created_by, created_at=request.created_at or _now(),
            amount_tolerance=request.amount_tolerance_percent / 100,
            date_window_days=request.date_window_days, classify_unmatched=request.classify_unmatched,
            classification_limit=request.classification_limit,
            preferred_provider=request.preferred_provider, preferred_model=request.preferred_model,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "transaction_reconciliation": record,
            "external_write_performed": False}


@router.get("/finance-transaction-reconciliation")
def get_finance_transaction_reconciliation(workspace_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        record = FinanceTransactionReconciliationService(get_business_container_repository()).latest(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "latest_transaction_reconciliation": record}


@router.post("/finance-transaction-match-review")
def review_finance_transaction_match(workspace_id: str, run_id: str, match_id: str,
                                     request: FinanceTransactionMatchReviewRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        record = FinanceTransactionReconciliationService(get_business_container_repository()).review(
            workspace_id, run_id, match_id, decision=request.decision,
            reviewed_by=request.reviewed_by, notes=request.notes, reviewed_at=request.reviewed_at or _now()
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "transaction_reconciliation": record,
            "external_write_performed": False, "provider_reconciliation_posted": False}


@router.post("/finance-counterparty-classification-review")
def review_finance_counterparty_classification(workspace_id: str, run_id: str, suggestion_id: str,
                                               request: FinanceCounterpartyClassificationReviewRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        record = FinanceTransactionReconciliationService(get_business_container_repository()).review_classification(
            workspace_id, run_id, suggestion_id, decision=request.decision,
            reviewed_by=request.reviewed_by, selected_account=request.selected_account,
            notes=request.notes, reviewed_at=request.reviewed_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "transaction_reconciliation": record,
            "external_write_performed": False}


@router.post("/finance-xero-reconciliation-handoff-prepare")
def prepare_xero_reconciliation_handoff(workspace_id: str, run_id: str, match_id: str,
                                        request: XeroReconciliationHandoffPrepareRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        reconciliation = FinanceTransactionReconciliationService(get_business_container_repository()).latest(workspace_id)
        if not reconciliation or reconciliation.get("run_id") != run_id:
            raise FileNotFoundError(f"Transaction reconciliation not found: {run_id}")
        handoff = XeroReconciliationHandoffService().prepare(
            workspace_id, reconciliation, match_id, prepared_by=request.prepared_by,
            prepared_at=request.prepared_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "handoff": handoff, "external_write_performed": False}


@router.get("/finance-xero-reconciliation-handoffs")
def list_xero_reconciliation_handoffs(workspace_id: str,
                                      limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        handoffs = XeroReconciliationHandoffService().list(workspace_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "handoffs": handoffs,
            "external_write_performed": False}


@router.post("/finance-xero-reconciliation-handoff-decision")
def decide_xero_reconciliation_handoff(workspace_id: str, handoff_id: str,
                                       request: XeroReconciliationHandoffDecisionRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        handoff = XeroReconciliationHandoffService().decide(
            workspace_id, handoff_id, approved=request.approved, decided_by=request.decided_by,
            decided_payload_hash=request.decided_payload_hash, reason=request.reason,
            decided_at=request.decided_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "handoff": handoff, "external_write_performed": False}


@router.post("/finance-xero-reconciliation-handoff-execute")
def execute_xero_reconciliation_handoff(workspace_id: str, handoff_id: str,
                                        request: XeroReconciliationHandoffExecuteRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        receipt = XeroReconciliationHandoffService().execute(
            workspace_id, handoff_id, attempted_by=request.attempted_by,
            attempted_at=request.attempted_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "receipt": receipt,
            "external_write_performed": False, "provider_reconciliation_posted": False}


@router.post("/finance-director-refresh")
def refresh_finance_director(workspace_id: str, request: FinanceDirectorRefreshRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        record = FinanceDirectorService(get_business_container_repository()).refresh(
            workspace_id, minimum_cash_reserve=request.minimum_cash_reserve,
            created_by=request.created_by, created_at=request.created_at or _now()
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "finance_director": record,
            "external_write_performed": False}


@router.get("/finance-director")
def get_finance_director(workspace_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        record = FinanceDirectorService(get_business_container_repository()).latest(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "finance_director": record}


@router.post("/{workspace_id}/finance/{task_id}/proposals")
def create_finance_controlled_proposal(workspace_id: str, task_id: str, request: FinanceControlledProposalRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        envelope = FinanceControlledActionService(get_department_pilot_repository()).propose(
            workspace_id, task_id, tool_call_id=request.tool_call_id,
            tool_name=request.tool_name, provider=request.provider, payload=request.payload,
            rationale=request.rationale, proposed_by=request.proposed_by,
            proposed_at=request.proposed_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (ValueError, DepartmentPilotConcurrencyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "external_action_performed": False, "envelope": envelope.model_dump(mode="json")}


@router.post("/{workspace_id}/finance/{task_id}/proposals/{tool_call_id}/decision")
def decide_finance_controlled_proposal(workspace_id: str, task_id: str, tool_call_id: str, request: FinanceControlledProposalDecisionRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        envelope = FinanceControlledActionService(get_department_pilot_repository()).decide(
            workspace_id, task_id, tool_call_id, approval_id=request.approval_id,
            approved=request.approved, decided_by=request.decided_by,
            decided_payload_hash=request.decided_payload_hash, reason=request.reason,
            decided_at=request.decided_at or _now(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (ValueError, DepartmentPilotConcurrencyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "external_action_performed": False, "envelope": envelope.model_dump(mode="json")}


@router.get("/{workspace_id}/finance/{task_id}/proposals/{tool_call_id}/readiness")
def finance_controlled_proposal_readiness(workspace_id: str, task_id: str, tool_call_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        return FinanceControlledActionService(get_department_pilot_repository()).execution_readiness(workspace_id, task_id, tool_call_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/finance-recurring")
def create_finance_recurring_schedule(workspace_id: str, request: FinanceRecurringScheduleRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        schedule = FinanceRecurringWorkService(get_business_container_repository()).create(
            workspace_id, schedule_id=request.schedule_id, kind=request.kind,
            cadence=request.cadence, next_run_at=request.next_run_at,
            created_by=request.created_by,
            minimum_cash_reserve=request.minimum_cash_reserve,
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "schedule": schedule}


@router.get("/finance-recurring")
def list_finance_recurring_schedules(workspace_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        schedules = FinanceRecurringWorkService(get_business_container_repository()).list(workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "schedules": schedules}


@router.post("/finance-recurring-enabled")
def set_finance_recurring_schedule_enabled(workspace_id: str, schedule_id: str, request: FinanceRecurringEnabledRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        schedule = FinanceRecurringWorkService(get_business_container_repository()).set_enabled(
            workspace_id, schedule_id, request.enabled
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, "schedule": schedule}


@router.post("/finance-recurring-run")
def run_finance_recurring_schedule(workspace_id: str, schedule_id: str, request: FinanceRecurringRunRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    try:
        result = FinanceRecurringWorkService(get_business_container_repository()).run(
            workspace_id, schedule_id, run_at=request.run_at, actor_id=request.actor_id
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "workspace_id": workspace_id, **result}


@router.post("/finance-recurring-run-due")
def run_due_finance_recurring_schedules(workspace_id: str, request: FinanceRecurringRunRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    results = FinanceRecurringWorkService(get_business_container_repository()).run_due(
        workspace_id, now=request.run_at
    )
    return {"ok": True, "workspace_id": workspace_id, "results": results}


@router.get("/{workspace_id}/{department_id}/{task_id}/diagnostics")
def get_department_task_diagnostics(workspace_id: str, department_id: str, task_id: str) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    _profile_or_404(department_id)
    try:
        return DepartmentPilotRecoveryService(get_department_pilot_repository()).diagnostics(
            workspace_id, department_id, task_id
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{workspace_id}/{department_id}/{task_id}/retry")
def retry_department_task(workspace_id: str, department_id: str, task_id: str, request: DepartmentTaskRecoveryRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    _profile_or_404(department_id)
    try:
        envelope = DepartmentPilotRecoveryService(get_department_pilot_repository()).retry(
            workspace_id, department_id, task_id, actor_id=request.actor_id,
            occurred_at=request.occurred_at, reason=request.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (ValueError, DepartmentPilotConcurrencyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "envelope": envelope.model_dump(mode="json")}


@router.post("/{workspace_id}/{department_id}/{task_id}/cancel")
def cancel_department_task(workspace_id: str, department_id: str, task_id: str, request: DepartmentTaskRecoveryRequest) -> dict[str, Any]:
    workspace_id = _canonical_workspace(workspace_id)
    _profile_or_404(department_id)
    try:
        envelope = DepartmentPilotRecoveryService(get_department_pilot_repository()).cancel(
            workspace_id, department_id, task_id, actor_id=request.actor_id,
            occurred_at=request.occurred_at, reason=request.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (ValueError, DepartmentPilotConcurrencyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "envelope": envelope.model_dump(mode="json")}
