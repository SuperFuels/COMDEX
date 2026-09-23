from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.pilot_operating_team_service import (
    DEPARTMENTS,
    PilotOperatingTeamService,
)


router = APIRouter(prefix="/api/aion/business/pilot-team", tags=["aion-pilot-operating-team"])
SERVICE = PilotOperatingTeamService()


def _call(method: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        return getattr(SERVICE, method)(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class BootstrapRequest(BaseModel):
    actor_id: str = "founder"
    departments: list[str] = Field(default_factory=lambda: list(DEPARTMENTS))


class ControlRequest(BaseModel):
    control_state: str
    controller_id: str
    reason: str


class DemonstrationRequest(BaseModel):
    name: str
    department_id: str
    outcome: str
    observed_steps: list[dict[str, Any]]
    created_by: str
    source_systems: list[str] = Field(default_factory=list)
    failure_policy: str = "stop_and_report"


class SkillValidationRequest(BaseModel):
    validated_by: str
    checks: dict[str, bool]
    publish: bool = False


class SkillUpdateRequest(BaseModel):
    name: str
    outcome: str
    updated_by: str = "person:founder"


class SkillDeleteRequest(BaseModel):
    deleted_by: str = "person:founder"


class WorkflowSkillCompletionRequest(BaseModel):
    completed_by: str
    succeeded: bool
    output: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    external_effect_performed: bool = False


class WorkflowSkillRunRequest(BaseModel):
    skill_hash: str
    workflow_id: str
    workflow_node_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str
    requested_by: str = "person:founder"


class RoutineRequest(BaseModel):
    title: str
    department_id: str
    owner_id: str
    skill_id: str | None = None
    workflow_id: str | None = None
    workflow_name: str | None = None
    workflow_graph: dict[str, Any] | None = None
    schedule: dict[str, Any] | None = None
    event_trigger: dict[str, Any] | None = None
    input_source: str
    expected_result: str
    access_contract: dict[str, Any] | None = None
    output_contract: dict[str, Any] | None = None
    approval_policy: str = "exact_payload_for_external_write"
    stale_data_policy: str = "stop_and_report"
    no_data_policy: str = "report_no_data"


class RoutineTestRequest(BaseModel):
    tested_by: str
    checks: dict[str, bool]


class RoutineEnabledRequest(BaseModel):
    enabled: bool
    changed_by: str


class EventDispatchRequest(BaseModel):
    event: dict[str, Any]
    trigger_instance_id: str


class MissionRequest(BaseModel):
    outcome: str
    requested_by: str
    constraints: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)


class DelegationRequest(BaseModel):
    department_id: str
    outcome: str
    delegated_by: str
    depth: int = 1
    depends_on: list[str] = Field(default_factory=list)


class MissionControlRequest(BaseModel):
    command: str
    actor_id: str
    instruction: str = ""


class CompletionPackRequest(BaseModel):
    facts: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    actions_completed: list[dict[str, Any]] = Field(default_factory=list)
    approvals_waiting: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    prepared_by: str


class MemoryRequest(BaseModel):
    department_id: str
    scope: str
    key: str
    value: Any
    actor_id: str
    authority_source: str | None = None
    mission_id: str | None = None


class WorkerNodeRequest(BaseModel):
    node_id: str
    label: str
    registered_by: str
    capabilities: list[str] = Field(default_factory=list)
    availability: str = "when_online"


class WorkerHeartbeatRequest(BaseModel):
    reported_by: str
    observed_capabilities: list[str] = Field(default_factory=list)


class TemplateRequest(BaseModel):
    name: str
    template_type: str
    source_id: str
    created_by: str
    include_sensitive_configuration: bool = False


class TemplateInstantiationRequest(BaseModel):
    created_by: str
    name: str | None = None
    department_id: str | None = None


class PreflightRequest(BaseModel):
    department_id: str
    initiator: dict[str, Any]
    action_type: str
    target: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    registered_capability: bool = False


@router.post("/{workspace_id}/bootstrap")
def bootstrap(workspace_id: str, request: BootstrapRequest) -> dict[str, Any]:
    return _call("bootstrap_workspace", workspace_id, departments=request.departments, actor_id=request.actor_id)


@router.get("/{workspace_id}")
def workspace(workspace_id: str) -> dict[str, Any]:
    return _call("workspace", workspace_id)


@router.post("/{workspace_id}/capsules/{department_id}/control")
def control_capsule(workspace_id: str, department_id: str, request: ControlRequest) -> dict[str, Any]:
    return _call(
        "transfer_control",
        workspace_id,
        department_id,
        control_state=request.control_state,
        controller_id=request.controller_id,
        reason=request.reason,
    )


@router.post("/{workspace_id}/skills/demonstrations")
def create_demonstration(workspace_id: str, request: DemonstrationRequest) -> dict[str, Any]:
    return _call("create_demonstrated_skill", workspace_id, **request.model_dump())


@router.post("/{workspace_id}/skills/{skill_id}/validate")
def validate_skill(workspace_id: str, skill_id: str, request: SkillValidationRequest) -> dict[str, Any]:
    return _call("validate_skill", workspace_id, skill_id, **request.model_dump())


@router.patch("/{workspace_id}/skills/{skill_id}")
def update_skill(workspace_id: str, skill_id: str, request: SkillUpdateRequest) -> dict[str, Any]:
    return _call("update_demonstrated_skill", workspace_id, skill_id, **request.model_dump())


@router.delete("/{workspace_id}/skills/{skill_id}")
def delete_skill(workspace_id: str, skill_id: str, request: SkillDeleteRequest) -> dict[str, Any]:
    return _call("archive_demonstrated_skill", workspace_id, skill_id, **request.model_dump())


@router.get("/{workspace_id}/skills/workflow-nodes")
def workflow_skill_nodes(workspace_id: str) -> dict[str, Any]:
    return _call("workflow_skill_nodes", workspace_id)


@router.post("/{workspace_id}/skills/{skill_id}/runs")
def queue_workflow_skill_run(
    workspace_id: str,
    skill_id: str,
    request: WorkflowSkillRunRequest,
) -> dict[str, Any]:
    return _call(
        "queue_workflow_skill_run",
        workspace_id,
        skill_id=skill_id,
        **request.model_dump(),
    )


@router.post("/{workspace_id}/skills/runs/{run_id}/complete")
def complete_workflow_skill_run(
    workspace_id: str,
    run_id: str,
    request: WorkflowSkillCompletionRequest,
) -> dict[str, Any]:
    return _call("complete_workflow_skill_run", workspace_id, run_id, **request.model_dump())


@router.post("/{workspace_id}/routines")
def create_routine(workspace_id: str, request: RoutineRequest) -> dict[str, Any]:
    return _call("create_routine", workspace_id, **request.model_dump())


@router.post("/{workspace_id}/routines/{routine_id}/test")
def test_routine(workspace_id: str, routine_id: str, request: RoutineTestRequest) -> dict[str, Any]:
    return _call("test_routine", workspace_id, routine_id, **request.model_dump())


@router.post("/{workspace_id}/routines/{routine_id}/enabled")
def set_routine_enabled(workspace_id: str, routine_id: str, request: RoutineEnabledRequest) -> dict[str, Any]:
    return _call("set_routine_enabled", workspace_id, routine_id, **request.model_dump())


@router.post("/{workspace_id}/events")
def dispatch_event(workspace_id: str, request: EventDispatchRequest) -> dict[str, Any]:
    return _call("dispatch_event", workspace_id, **request.model_dump())


@router.post("/{workspace_id}/routines/run-due")
def run_due_routines(workspace_id: str) -> dict[str, Any]:
    return _call("run_due_routines", workspace_id)


@router.post("/{workspace_id}/missions")
def create_mission(workspace_id: str, request: MissionRequest) -> dict[str, Any]:
    return _call("create_mission", workspace_id, **request.model_dump())


@router.post("/{workspace_id}/missions/launch")
def launch_mission(workspace_id: str, request: MissionRequest) -> dict[str, Any]:
    return _call("launch_mission", workspace_id, **request.model_dump())


@router.post("/{workspace_id}/missions/{mission_id}/delegate")
def delegate(workspace_id: str, mission_id: str, request: DelegationRequest) -> dict[str, Any]:
    return _call("delegate", workspace_id, mission_id, **request.model_dump())


@router.post("/{workspace_id}/missions/{mission_id}/control")
def control_mission(workspace_id: str, mission_id: str, request: MissionControlRequest) -> dict[str, Any]:
    return _call("control_mission", workspace_id, mission_id, **request.model_dump())


@router.post("/{workspace_id}/missions/{mission_id}/completion-pack")
def completion_pack(workspace_id: str, mission_id: str, request: CompletionPackRequest) -> dict[str, Any]:
    return _call("completion_pack", workspace_id, mission_id, **request.model_dump())


@router.post("/{workspace_id}/memory")
def remember(workspace_id: str, request: MemoryRequest) -> dict[str, Any]:
    return _call("remember", workspace_id, **request.model_dump())


@router.post("/{workspace_id}/worker-nodes")
def register_worker(workspace_id: str, request: WorkerNodeRequest) -> dict[str, Any]:
    return _call("register_worker_node", workspace_id, **request.model_dump())


@router.post("/{workspace_id}/worker-nodes/{node_id}/heartbeat")
def heartbeat_worker(
    workspace_id: str,
    node_id: str,
    request: WorkerHeartbeatRequest,
) -> dict[str, Any]:
    return _call("heartbeat_worker_node", workspace_id, node_id, **request.model_dump())


@router.post("/{workspace_id}/templates")
def save_template(workspace_id: str, request: TemplateRequest) -> dict[str, Any]:
    return _call("save_template", workspace_id, **request.model_dump())


@router.post("/{workspace_id}/templates/{template_id}/instantiate")
def instantiate_template(
    workspace_id: str,
    template_id: str,
    request: TemplateInstantiationRequest,
) -> dict[str, Any]:
    return _call("instantiate_template", workspace_id, template_id, **request.model_dump())


@router.post("/{workspace_id}/actions/preflight")
def preflight(workspace_id: str, request: PreflightRequest) -> dict[str, Any]:
    return _call("preflight_action", workspace_id, **request.model_dump())


@router.get("/{workspace_id}/audit/verify")
def verify_audit(workspace_id: str) -> dict[str, Any]:
    return _call("verify_audit", workspace_id)
