from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.modules.aion_fabric.canonical import utc_now_iso
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.runtime.department_pilot_repository import DepartmentPilotRepository
from backend.modules.aion_business.runtime.finance_pilot_conversation_service import FinancePilotConversationService
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository
from backend.modules.pilot_unified.workspace_gateway import AionBoardroomWorkspaceProvider

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
from backend.modules.aion_business.runtime.aion_flow_execution import (
    AionFlowExecutionService,
)
from backend.modules.aion_business.runtime.aion_flow_evaluation import AionFlowEvaluationService
from backend.modules.aion_business.runtime.aion_flow_templates import AionFlowTemplateLibrary
from backend.modules.aion_business.runtime.aion_flow_production import AionFlowProductionService
from backend.modules.aion_business.runtime.aion_flow_authority import AionFlowWorkspaceAuthority
from backend.modules.aion_business.runtime.aion_flow_policy import AionFlowPolicyStore
from backend.modules.aion_business.runtime.aion_flow_session_authority import (
    AionFlowSessionAuthority,
    VerifiedAionFlowSession,
)
from backend.modules.aion_business.runtime.operations_executive_briefing_service import (
    EXECUTIVE_MESSAGE_TYPES,
    OperationsExecutiveBriefingService,
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


class AionFlowPrepareRequest(BaseModel):
    graph: Dict[str, Any]
    actor: Dict[str, Any]
    policy: Dict[str, Any]
    approvals: List[Dict[str, Any]] = Field(default_factory=list)
    inputs: Dict[str, Any] = Field(default_factory=dict)


class AionFlowExecuteRequest(BaseModel):
    preparation_id: str
    review_hash: str
    exact_confirmed: bool = False
    inputs: Dict[str, Any] = Field(default_factory=dict)
    execution_mode: str = "connector_ready"


class AionFlowAuthorizeRequest(BaseModel):
    preparation_id: str
    review_hash: str
    approver_person_id: str
    exact_confirmed: bool = False


class AionFlowControlRequest(BaseModel):
    action: str
    preparation_id: str = ""


class AionFlowEvaluationCreateRequest(BaseModel):
    graph: Dict[str, Any]
    node_id: str
    challenger_value: str
    evidence_pack: Dict[str, Any] = Field(default_factory=dict)
    measure_scope: str = "customer_private"
    traffic_fraction: float = Field(default=0.1, gt=0, le=0.5)
    minimum_samples: int = Field(default=3, ge=1, le=10000)


class AionFlowEvaluationResultRequest(BaseModel):
    variant: str
    result: Dict[str, Any]


class AionFlowEvaluationDecisionRequest(BaseModel):
    actor_id: str
    reason: str = ""


class AionFlowEvaluationRunRequest(BaseModel):
    actor: Dict[str, Any]
    policy: Dict[str, Any]


class AionFlowTemplateInstallRequest(BaseModel):
    organisation_id: str
    bindings: Dict[str, str] = Field(default_factory=dict)
    actor_role: str = "owner"


class AionFlowTemplateLifecycleRequest(BaseModel):
    action: str
    reason: str
    actor_role: str = "owner"


class AionFlowTemplatePinRequest(BaseModel):
    template_ref: str
    actor_role: str = "owner"


class AionFlowTemplateRoleRequest(BaseModel):
    actor_role: str = "owner"


class AionFlowProductionRequest(BaseModel):
    graph: Dict[str, Any]
    actor: Dict[str, Any]
    mode: str = "author"
    base_revision: int = 0


class AionFlowEncryptedTransferRequest(BaseModel):
    graph: Dict[str, Any] = Field(default_factory=dict)
    package: Dict[str, Any] = Field(default_factory=dict)
    password: str
    actor: Dict[str, Any]


class AionFlowProductionHistoryRequest(BaseModel):
    workflow_id: str
    actor: Dict[str, Any]


class AionFlowProductionDiffRequest(AionFlowProductionHistoryRequest):
    left: int
    right: int


class AionFlowPolicyRequest(BaseModel):
    policy: Dict[str, Any]
    expected_revision: int = Field(ge=1)


class AionFlowLoadQualificationRequest(BaseModel):
    large_nodes: int = Field(default=1500, ge=100, le=5000)
    parallel_routes: int = Field(default=256, ge=2, le=2000)
    checkpoints: int = Field(default=250, ge=10, le=5000)


def get_runner() -> WorkflowCapsuleRunner:
    return WorkflowCapsuleRunner()


def get_intent_resolver() -> WorkflowIntentResolver:
    return WorkflowIntentResolver()


def get_approval_store() -> WorkflowCapsuleApprovalStore:
    return WorkflowCapsuleApprovalStore()


def get_aion_flow_execution_service() -> AionFlowExecutionService:
    return AionFlowExecutionService()


def get_aion_flow_evaluation_service() -> AionFlowEvaluationService:
    return AionFlowEvaluationService()


def get_aion_flow_template_library() -> AionFlowTemplateLibrary:
    return AionFlowTemplateLibrary()


def get_aion_flow_production_service() -> AionFlowProductionService:
    return AionFlowProductionService()


_aion_flow_session_authority = AionFlowSessionAuthority()


def _operations_conversation_page(workspace_id: str, department_id: str = "operations", before: str = "", limit: int = 50) -> Dict[str, Any]:
    """Read a bounded page from the protected workspace COO stream."""
    repository = BusinessContainerRepository()
    runtime = repository.load_optional_dict(workspace_id, "operational_runtime_summary") or {}
    store = runtime.get("shared_conversations") if isinstance(runtime.get("shared_conversations"), dict) else {}
    turns = [
        dict(item) for item in store.get("turns") or []
        if isinstance(item, dict) and str(item.get("message_type") or "") not in EXECUTIVE_MESSAGE_TYPES
    ]
    department = str(department_id or "operations").strip().lower()[:80]
    turns = [item for item in turns if item.get("department_id") == department]
    turns.sort(key=lambda item: (int(item.get("sequence") or 0), str(item.get("created_at") or ""), str(item.get("id") or "")))
    if before:
        index = next((i for i, item in enumerate(turns) if str(item.get("id") or "") == before), len(turns))
        turns = turns[:index]
    size = max(10, min(int(limit or 50), 75))
    page = turns[-size:]
    return {"ok": True, "workspace_id": workspace_id, "department_id": department, "turns": page,
            "has_more": len(turns) > len(page), "next_before": str(page[0].get("id") or "") if len(turns) > len(page) and page else "",
            "retention": {"recent_window": 75, "page_size": size, "archive_searchable": True}}


async def require_aion_flow_session(request: Request) -> VerifiedAionFlowSession:
    try:
        body = await request.body()
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return _aion_flow_session_authority.verify(method=request.method, target=target, body=body, headers=request.headers)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class OperationsConversationHistoryRequest(BaseModel):
    department_id: str = "operations"
    before: str = ""
    limit: int = Field(default=50, ge=10, le=75)


class OperationsConversationAppendRequest(BaseModel):
    department_id: str = "operations"
    role: str = "user"
    content: str = Field(min_length=1, max_length=2000)


class OperationsConversationTurnRequest(BaseModel):
    department_id: str = "operations"
    user_text: str = Field(min_length=1, max_length=2000)
    attachments: list[str] = Field(default_factory=list, max_length=3)


class OperationsDepartmentChannelRequest(BaseModel):
    department_id: str
    limit: int = Field(default=75, ge=10, le=100)


class OperationsDepartmentTurnRequest(BaseModel):
    department_id: str
    user_text: str = Field(min_length=1, max_length=2000)


class OperationsMorningBriefingRequest(BaseModel):
    force: bool = False


def _operations_workspace_provider() -> AionBoardroomWorkspaceProvider:
    return AionBoardroomWorkspaceProvider(
        WorkspaceRepository(), BusinessContainerRepository(), DepartmentPilotRepository(),
        FinancePilotConversationService(), WorkflowFileCabinetRepository,
    )


def _operations_executive_service() -> OperationsExecutiveBriefingService:
    return OperationsExecutiveBriefingService(_operations_workspace_provider())


@router.post("/aion-flow/operations-conversation/history")
def read_operations_conversation(
    payload: OperationsConversationHistoryRequest,
    session: VerifiedAionFlowSession = Depends(require_aion_flow_session),
) -> Dict[str, Any]:
    # The possession-bound desktop session determines both the person and the
    # workspace.  Browser input never selects another business record.
    return _operations_conversation_page(session.workspace_id, payload.department_id, payload.before, payload.limit)


@router.post("/aion-flow/operations-conversation/append")
def append_operations_conversation(
    payload: OperationsConversationAppendRequest,
    session: VerifiedAionFlowSession = Depends(require_aion_flow_session),
) -> Dict[str, Any]:
    role = payload.role.strip().lower()
    content = " ".join(payload.content.split())[:2000]
    if role not in {"user", "assistant"} or not content:
        raise HTTPException(status_code=422, detail="A conversation message needs a valid role and content")
    department = payload.department_id.strip().lower()[:80] or "operations"
    repository = BusinessContainerRepository()
    runtime = repository.load_optional_dict(session.workspace_id, "operational_runtime_summary") or {}
    store = runtime.get("shared_conversations") if isinstance(runtime.get("shared_conversations"), dict) else {"schema_version": "workspace_conversation_v1", "turns": []}
    turns = [dict(item) for item in store.get("turns") or [] if isinstance(item, dict)]
    message = {"id": f"msg-{uuid4().hex}", "sequence": len(turns), "department_id": department, "role": role,
               "sender": session.person_id if role == "user" else "Operations Pilot", "content": content,
               "created_at": utc_now_iso(), "approval_gated": True,
               "source": "signed_desktop_session"}
    turns.append(message)
    runtime["shared_conversations"] = {"schema_version": "workspace_conversation_v1", "turns": turns[-1200:], "updated_at": message["created_at"]}
    repository.save_dict(session.workspace_id, "operational_runtime_summary", runtime)
    return {"ok": True, "message": message, "history": _operations_conversation_page(session.workspace_id, department)}


@router.post("/aion-flow/operations-conversation/turn")
def run_operations_conversation_turn(
    payload: OperationsConversationTurnRequest,
    session: VerifiedAionFlowSession = Depends(require_aion_flow_session),
) -> Dict[str, Any]:
    """Run the same read-only COO mission used by the paired phone.

    The signed desktop session fixes both actor and workspace; a browser cannot
    select another workspace or invoke a write-capable tool through this route.
    """
    try:
        response = _operations_workspace_provider().conversation_turn(
            session.workspace_id, payload.department_id, payload.user_text,
            persona_id=session.person_id, attachments=payload.attachments,
        )
    except (OSError, ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "conversation": response, "history": _operations_conversation_page(session.workspace_id, payload.department_id)}


@router.post("/aion-flow/operations-conversation/executive-status")
def read_operations_executive_status(
    session: VerifiedAionFlowSession = Depends(require_aion_flow_session),
) -> Dict[str, Any]:
    return _operations_executive_service().status(session.workspace_id)


@router.post("/aion-flow/operations-conversation/channel-history")
def read_operations_department_channel(
    payload: OperationsDepartmentChannelRequest,
    session: VerifiedAionFlowSession = Depends(require_aion_flow_session),
) -> Dict[str, Any]:
    try:
        return _operations_executive_service().channel_history(
            session.workspace_id, payload.department_id, limit=payload.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/aion-flow/operations-conversation/channel-turn")
def run_operations_department_turn(
    payload: OperationsDepartmentTurnRequest,
    session: VerifiedAionFlowSession = Depends(require_aion_flow_session),
) -> Dict[str, Any]:
    try:
        return _operations_executive_service().channel_turn(
            session.workspace_id, payload.department_id, payload.user_text,
            person_id=session.person_id,
        )
    except (OSError, ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/aion-flow/operations-conversation/morning-briefing")
def run_operations_morning_briefing(
    payload: OperationsMorningBriefingRequest,
    session: VerifiedAionFlowSession = Depends(require_aion_flow_session),
) -> Dict[str, Any]:
    try:
        return _operations_executive_service().run_morning_briefing(
            session.workspace_id, person_id=session.person_id, force=payload.force,
        )
    except (OSError, ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def authorize_aion_flow_session(
    session: VerifiedAionFlowSession,
    capability: str,
    *,
    claimed_actor: Dict[str, Any] | None = None,
    graph: Dict[str, Any] | None = None,
    expected_workspace_id: str | None = None,
    expected_organisation_id: str | None = None,
) -> Dict[str, Any]:
    actor = session.actor()
    claimed = claimed_actor or {}
    if claimed:
        claimed_person = str(claimed.get("person_id") or claimed.get("actor_id") or "")
        claimed_workspace = str(claimed.get("workspace_id") or "")
        if claimed_person and claimed_person != session.person_id:
            raise HTTPException(status_code=403, detail="signed_person_payload_mismatch")
        if claimed_workspace and claimed_workspace != session.workspace_id:
            raise HTTPException(status_code=403, detail="signed_workspace_payload_mismatch")
    decision = AionFlowWorkspaceAuthority().authorize(
        actor, capability, graph=graph, expected_workspace_id=expected_workspace_id,
        expected_organisation_id=expected_organisation_id,
    )
    if decision.get("allowed") is not True:
        raise HTTPException(status_code=403, detail=str(decision.get("reason") or "canonical_aion_flow_authority_denied"))
    return {**actor, "authority_decision": decision}


@router.post("/aion-flow/prepare")
def prepare_aion_flow(payload: AionFlowPrepareRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    """Compile, statically validate and simulate a visible AION Flow without executing it."""
    actor = authorize_aion_flow_session(session, "aion_flow.prepare", claimed_actor=payload.actor, graph=payload.graph)
    policy = AionFlowPolicyStore().governance_policy(session.workspace_id)
    result = get_aion_flow_execution_service().prepare(
        graph=payload.graph,
        actor=actor,
        policy=policy,
        approvals=payload.approvals,
        inputs=payload.inputs,
    )
    result["policy_source"] = "signed_customer_execution_policy"
    result["browser_policy_ignored"] = True
    return result


@router.post("/aion-flow/execute")
def execute_aion_flow(payload: AionFlowExecuteRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    service = get_aion_flow_execution_service()
    prepared = service.repository.get_prepared(payload.preparation_id)
    if not prepared:
        raise HTTPException(status_code=404, detail="Prepared AION Flow route not found")
    context = (prepared.get("authorization_context") or {}).get("actor") or {}
    authorize_aion_flow_session(session, "aion_flow.execute", expected_workspace_id=str(context.get("workspace_id") or ""), expected_organisation_id=str(context.get("organisation_id") or ""))
    return service.execute(
        prepared=prepared,
        review_hash=payload.review_hash,
        exact_confirmed=payload.exact_confirmed,
        inputs=payload.inputs,
        execution_mode=payload.execution_mode,
    )


@router.post("/aion-flow/authorize")
def authorize_aion_flow(payload: AionFlowAuthorizeRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    service = get_aion_flow_execution_service()
    prepared = service.repository.get_prepared(payload.preparation_id)
    if not prepared:
        raise HTTPException(status_code=404, detail="Prepared AION Flow route not found")
    context = (prepared.get("authorization_context") or {}).get("actor") or {}
    authorize_aion_flow_session(session, "aion_flow.approve", expected_workspace_id=str(context.get("workspace_id") or ""), expected_organisation_id=str(context.get("organisation_id") or ""))
    if payload.approver_person_id != session.person_id:
        raise HTTPException(status_code=403, detail="approver_must_match_signed_person")
    return service.authorize_prepared(
        prepared=prepared,
        review_hash=payload.review_hash,
        approver_person_id=payload.approver_person_id,
        exact_confirmed=payload.exact_confirmed,
    )


@router.get("/aion-flow/runs")
def list_aion_flow_runs(limit: int = Query(default=25, ge=1, le=100), session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.view_runs")
    items = [item for item in get_aion_flow_execution_service().repository.list(limit=100) if str((item.get("authority_context") or {}).get("workspace_id") or "") == session.workspace_id][:limit]
    return {"ok": True, "items": items, "count": len(items)}


@router.get("/aion-flow/runs/{run_id}")
def get_aion_flow_run(run_id: str, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    item = get_aion_flow_execution_service().repository.get(run_id)
    if not item:
        raise HTTPException(status_code=404, detail="AION Flow run not found")
    authorize_aion_flow_session(session, "aion_flow.view_runs", expected_workspace_id=str((item.get("authority_context") or {}).get("workspace_id") or ""))
    return {"ok": True, "run": item}


@router.post("/aion-flow/runs/{run_id}/control")
def control_aion_flow_run(run_id: str, payload: AionFlowControlRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    service = get_aion_flow_execution_service()
    run = service.repository.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="AION Flow run not found")
    authorize_aion_flow_session(session, "aion_flow.control", expected_workspace_id=str((run.get("authority_context") or {}).get("workspace_id") or ""))
    prepared = service.repository.get_prepared(payload.preparation_id) if payload.preparation_id else None
    return service.control(run_id, payload.action, prepared=prepared)


@router.post("/aion-flow/recover")
def recover_aion_flow_runs(session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.control")
    return get_aion_flow_execution_service().recover_interrupted(workspace_id=session.workspace_id)


@router.post("/aion-flow/evaluations")
def create_aion_flow_evaluation(payload: AionFlowEvaluationCreateRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.evaluate", graph=payload.graph)
    try:
        item = get_aion_flow_evaluation_service().create(**payload.model_dump(), authority_context=actor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "evaluation": item}


@router.get("/aion-flow/evaluations")
def list_aion_flow_evaluations(limit: int = Query(default=25, ge=1, le=100), session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.evaluate")
    return {"ok": True, **get_aion_flow_evaluation_service().list(limit=limit, workspace_id=session.workspace_id)}


@router.get("/aion-flow/evaluations/{experiment_id}")
def get_aion_flow_evaluation(experiment_id: str, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    try:
        item = get_aion_flow_evaluation_service().get(experiment_id)
        authorize_aion_flow_session(session, "aion_flow.evaluate", expected_workspace_id=str((item.get("authority_context") or {}).get("workspace_id") or ""))
        return {"ok": True, "evaluation": item}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/aion-flow/evaluations/{experiment_id}/results")
def record_aion_flow_evaluation_result(experiment_id: str, payload: AionFlowEvaluationResultRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    try:
        current = get_aion_flow_evaluation_service().get(experiment_id)
        authorize_aion_flow_session(session, "aion_flow.evaluate", expected_workspace_id=str((current.get("authority_context") or {}).get("workspace_id") or ""))
        item = get_aion_flow_evaluation_service().record(experiment_id, variant=payload.variant, result=payload.result)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "evaluation": item}


@router.post("/aion-flow/evaluations/{experiment_id}/run-same-pack")
def run_aion_flow_evaluation_pair(experiment_id: str, payload: AionFlowEvaluationRunRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    execution = get_aion_flow_execution_service()
    current = get_aion_flow_evaluation_service().get(experiment_id)
    actor = authorize_aion_flow_session(session, "aion_flow.evaluate", claimed_actor=payload.actor, expected_workspace_id=str((current.get("authority_context") or {}).get("workspace_id") or ""))
    policy = AionFlowPolicyStore().governance_policy(session.workspace_id)

    def runner(graph: Dict[str, Any], evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
        prepared = execution.prepare(
            graph=graph,
            actor=actor,
            policy=policy,
            inputs={"evidence_pack": evidence_pack},
        )
        simulation = prepared.get("simulation") or {}
        nodes = simulation.get("nodes") or []
        node_count = max(1, len(graph.get("nodes") or []))
        verified = sum(1 for item in nodes if item.get("status") in {"verified", "simulated"})
        return {
            "ok": prepared.get("ok") is True,
            "phase": prepared.get("phase") or "simulation",
            "metrics": {
                "quality": 1.0 if prepared.get("ok") is True else 0.0,
                "correctness": 1.0 if prepared.get("static_validation", {}).get("ok") is True else 0.0,
                "evidence_coverage": verified / node_count,
                "latency_ms": 0,
                "cost": float(prepared.get("dry_run", {}).get("predicted", {}).get("estimated_cost") or 0),
                "energy_wh": 0,
            },
            "preparation_id": prepared.get("preparation_id"),
            "external_writes": 0,
        }

    try:
        item = get_aion_flow_evaluation_service().run_same_pack(experiment_id, runner=runner)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "evaluation": item}


@router.post("/aion-flow/evaluations/{experiment_id}/promote")
def promote_aion_flow_evaluation(experiment_id: str, payload: AionFlowEvaluationDecisionRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    try:
        current = get_aion_flow_evaluation_service().get(experiment_id)
        authorize_aion_flow_session(session, "aion_flow.evaluate", expected_workspace_id=str((current.get("authority_context") or {}).get("workspace_id") or ""))
        if payload.actor_id != session.person_id:
            raise HTTPException(status_code=403, detail="evaluation_actor_must_match_signed_person")
        item = get_aion_flow_evaluation_service().promote(experiment_id, actor_id=session.person_id, reason=payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "evaluation": item}


@router.post("/aion-flow/evaluations/{experiment_id}/reverse")
def reverse_aion_flow_evaluation(experiment_id: str, payload: AionFlowEvaluationDecisionRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    try:
        current = get_aion_flow_evaluation_service().get(experiment_id)
        authorize_aion_flow_session(session, "aion_flow.evaluate", expected_workspace_id=str((current.get("authority_context") or {}).get("workspace_id") or ""))
        if payload.actor_id != session.person_id:
            raise HTTPException(status_code=403, detail="evaluation_actor_must_match_signed_person")
        item = get_aion_flow_evaluation_service().reverse(experiment_id, actor_id=session.person_id, reason=payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "evaluation": item}


@router.get("/aion-flow/templates")
def list_aion_flow_templates() -> Dict[str, Any]:
    return {"ok": True, **get_aion_flow_template_library().list()}


@router.get("/aion-flow/templates/{template_ref}")
def inspect_aion_flow_template(template_ref: str) -> Dict[str, Any]:
    try:
        return {"ok": True, "template": get_aion_flow_template_library().inspect(template_ref)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/aion-flow/templates/{template_ref}/install")
def install_aion_flow_template(template_ref: str, payload: AionFlowTemplateInstallRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.template_manage", expected_organisation_id=payload.organisation_id)
    try:
        installed = get_aion_flow_template_library().install(template_ref, organisation_id=session.workspace_id, bindings=payload.bindings, actor_role="canonical_authority")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "installation": installed}


@router.post("/aion-flow/templates/{template_ref}/lifecycle")
def change_aion_flow_template_lifecycle(template_ref: str, payload: AionFlowTemplateLifecycleRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.template_manage")
    try:
        item = get_aion_flow_template_library().lifecycle(template_ref, action=payload.action, reason=payload.reason, actor_role="canonical_authority")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "template": item}


@router.get("/aion-flow/template-installations")
def list_aion_flow_template_installations(organisation_id: str = Query(..., min_length=1), session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.template_manage", expected_organisation_id=organisation_id)
    return {"ok": True, **get_aion_flow_template_library().list_installations(organisation_id=session.workspace_id)}


@router.post("/aion-flow/template-installations/{installation_id}/pin")
def pin_aion_flow_template_installation(installation_id: str, payload: AionFlowTemplatePinRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.template_manage")
    try:
        item = get_aion_flow_template_library().pin(installation_id, template_ref=payload.template_ref, actor_role="canonical_authority")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "installation": item}


@router.post("/aion-flow/template-installations/{installation_id}/rollback")
def rollback_aion_flow_template_installation(installation_id: str, payload: AionFlowTemplateRoleRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.template_manage")
    try:
        item = get_aion_flow_template_library().rollback(installation_id, actor_role="canonical_authority")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "installation": item}


@router.post("/aion-flow/template-installations/{installation_id}/remove")
def remove_aion_flow_template_installation(installation_id: str, payload: AionFlowTemplateRoleRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.template_manage")
    try:
        item = get_aion_flow_template_library().remove(installation_id, actor_role="canonical_authority")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "installation": item}


@router.post("/aion-flow/production/qualify")
def qualify_aion_flow_for_production(payload: AionFlowProductionRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.review", claimed_actor=payload.actor, graph=payload.graph)
    return {"ok": True, "qualification": get_aion_flow_production_service().qualify(payload.graph, actor=actor, mode=payload.mode)}


@router.post("/aion-flow/production/commit")
def commit_aion_flow_revision(payload: AionFlowProductionRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.commit", claimed_actor=payload.actor, graph=payload.graph)
    try:
        item = get_aion_flow_production_service().commit(payload.graph, actor=actor, base_revision=payload.base_revision)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "revision": item}


@router.post("/aion-flow/production/history")
def get_aion_flow_revision_history(payload: AionFlowProductionHistoryRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.review", claimed_actor=payload.actor)
    try:
        return {"ok": True, **get_aion_flow_production_service().history(payload.workflow_id, actor=actor)}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/aion-flow/production/diff")
def get_aion_flow_revision_diff(payload: AionFlowProductionDiffRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.review", claimed_actor=payload.actor)
    try:
        return {"ok": True, "diff": get_aion_flow_production_service().diff(payload.workflow_id, payload.left, payload.right, actor=actor)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/aion-flow/production/export")
def export_aion_flow_encrypted(payload: AionFlowEncryptedTransferRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.export", claimed_actor=payload.actor, graph=payload.graph)
    try:
        package = get_aion_flow_production_service().encrypted_export(payload.graph, password=payload.password, actor=actor)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "package": package}


@router.post("/aion-flow/production/import")
def import_aion_flow_encrypted(payload: AionFlowEncryptedTransferRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.import", claimed_actor=payload.actor)
    try:
        item = get_aion_flow_production_service().encrypted_import(payload.package, password=payload.password, actor=actor)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail="encrypted_import_failed") from exc
    return {"ok": True, **item}


@router.post("/aion-flow/production/telemetry")
def get_aion_flow_zero_content_telemetry(payload: AionFlowProductionRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.review", claimed_actor=payload.actor, graph=payload.graph)
    try:
        return {"ok": True, "telemetry": get_aion_flow_production_service().telemetry(payload.graph, actor=actor)}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/aion-flow/production/benchmark")
def benchmark_aion_flow(payload: AionFlowProductionRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.benchmark", claimed_actor=payload.actor, graph=payload.graph)
    try:
        return {"ok": True, "benchmark": get_aion_flow_production_service().benchmark(payload.graph, actor=actor)}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/aion-flow/production/load-qualification")
def qualify_aion_flow_load(payload: AionFlowLoadQualificationRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    actor = authorize_aion_flow_session(session, "aion_flow.benchmark")
    try:
        report = get_aion_flow_production_service().load_qualification(
            actor=actor,
            large_nodes=payload.large_nodes,
            parallel_routes=payload.parallel_routes,
            checkpoints=payload.checkpoints,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": report["passed"], "qualification": report}


@router.get("/aion-flow/policy")
def get_aion_flow_policy(session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.review")
    return {"ok": True, "policy": AionFlowPolicyStore().effective(session.workspace_id)}


@router.post("/aion-flow/policy")
def configure_aion_flow_policy(payload: AionFlowPolicyRequest, session: VerifiedAionFlowSession = Depends(require_aion_flow_session)) -> Dict[str, Any]:
    authorize_aion_flow_session(session, "aion_flow.policy_manage")
    try:
        policy = AionFlowPolicyStore().configure(session.workspace_id, payload.policy, changed_by=session.person_id, expected_revision=payload.expected_revision)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "policy": policy}


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
