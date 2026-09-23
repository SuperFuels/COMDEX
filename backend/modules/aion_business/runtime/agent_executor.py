from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.tasks import LearningRecord, TaskRecord
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.agent_lifecycle import AgentLifecycle
from backend.modules.aion_business.runtime.agent_repository import AgentRepository
from backend.modules.aion_business.runtime.audit_log import AuditLog
from backend.modules.aion_business.runtime.escalation import EscalationHandler
from backend.modules.aion_business.runtime.learning_service import LearningService
from backend.modules.aion_business.runtime.task_record_repository import TaskRecordRepository
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.workflows.campaign_planning import CampaignPlanningWorkflow


class AgentExecutionResult(dict):
    @property
    def ok(self) -> bool:
        return bool(self.get("ok", False))


class AgentExecutor:
    """
    Executes persisted task agents.

    v4 behavior:
    - success path remains unchanged
    - failures can escalate tasks through EscalationHandler
    - learning records are captured and persisted through LearningService
    """

    def __init__(
        self,
        agent_repository: Optional[AgentRepository] = None,
        task_repository: Optional[TaskRecordRepository] = None,
        workspace_repository: Optional[WorkspaceRepository] = None,
        lifecycle: Optional[AgentLifecycle] = None,
        audit_log: Optional[AuditLog] = None,
        escalation_handler: Optional[EscalationHandler] = None,
        learning_service: Optional[LearningService] = None,
        campaign_planning_workflow: Optional[CampaignPlanningWorkflow] = None,
    ):
        self.agent_repository = agent_repository or AgentRepository()
        self.task_repository = task_repository or TaskRecordRepository()
        self.workspace_repository = workspace_repository or WorkspaceRepository()
        self.lifecycle = lifecycle or AgentLifecycle()
        self.audit_log = audit_log or AuditLog()
        self.escalation_handler = escalation_handler or EscalationHandler(
            task_repository=self.task_repository,
            audit_log=self.audit_log,
        )
        self.learning_service = learning_service or LearningService()
        self.campaign_planning_workflow = (
            campaign_planning_workflow or CampaignPlanningWorkflow()
        )

    def execute_task_agent(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        task_id: str,
        role: RoleSpec,
        execution_notes: Optional[Dict[str, Any]] = None,
    ) -> AgentExecutionResult:
        agent = self.agent_repository.load(workspace_id, agent_id)
        task = self.task_repository.load(workspace_id, task_id)
        workspace = self.workspace_repository.load(workspace_id)

        self._validate_assignment(agent=agent, task=task, role=role, workspace=workspace)

        notes = execution_notes or {}
        trace: List[Dict[str, Any]] = []

        try:
            agent = self.lifecycle.transition(workspace_id, agent.id, "initialized")
            trace.append({"state": agent.lifecycle_state, "message": "agent initialized"})
            self.audit_log.log_agent_transition(
                workspace_id=workspace_id,
                role_id=role.id,
                agent_id=agent.id,
                task_id=task.id,
                from_state="spawned",
                to_state="initialized",
            )

            task.status = "running"
            if not task.started_at:
                task.started_at = self.lifecycle.utc_now_iso()
            task.updated_at = self.lifecycle.utc_now_iso()
            self.task_repository.save(task)

            agent = self.lifecycle.transition(workspace_id, agent.id, "running")
            trace.append({"state": agent.lifecycle_state, "message": "agent running"})
            self.audit_log.log_agent_transition(
                workspace_id=workspace_id,
                role_id=role.id,
                agent_id=agent.id,
                task_id=task.id,
                from_state="initialized",
                to_state="running",
            )

            self.audit_log.log_trace(
                workspace_id=workspace_id,
                trace_type="agent_trace",
                agent_id=agent.id,
                task_id=task.id,
                stage="execution_started",
                message="Agent execution started",
                data={
                    "task_type": task.inputs.get("task_type"),
                    "role_id": role.id,
                },
            )

            execution_result = self._dispatch_execution(
                workspace=workspace,
                role=role,
                agent=agent,
                task=task,
                notes=notes,
            )

            task.outputs = execution_result["output"]
            task.status = "completed"
            task.completed_at = self.lifecycle.utc_now_iso()
            task.updated_at = self.lifecycle.utc_now_iso()
            self.task_repository.save(task)

            learning_records = self._capture_and_persist_learning(
                workspace_id=workspace_id,
                task=task,
                role=role,
            )

            agent = self.lifecycle.transition(workspace_id, agent.id, "completed")
            trace.append({"state": agent.lifecycle_state, "message": "agent completed"})
            self.audit_log.log_agent_transition(
                workspace_id=workspace_id,
                role_id=role.id,
                agent_id=agent.id,
                task_id=task.id,
                from_state="running",
                to_state="completed",
            )

            self.audit_log.log_trace(
                workspace_id=workspace_id,
                trace_type="agent_trace",
                agent_id=agent.id,
                task_id=task.id,
                stage="execution_completed",
                message="Agent execution completed",
                data={
                    "mode": execution_result["mode"],
                    "task_type": task.inputs.get("task_type"),
                    "learning_record_ids": [r.id for r in learning_records],
                },
            )

            return AgentExecutionResult(
                ok=True,
                workspace_id=workspace_id,
                agent_id=agent.id,
                task_id=task.id,
                agent_state=agent.lifecycle_state,
                task_status=task.status,
                trace=trace,
                output=execution_result["output"],
                mode=execution_result["mode"],
                learning_record_ids=[r.id for r in learning_records],
            )

        except Exception as exc:
            error_message = f"{type(exc).__name__}: {exc}"

            task.status = "failed"
            task.updated_at = self.lifecycle.utc_now_iso()
            task.outputs["error"] = error_message
            self.task_repository.save(task)

            current_state = self.agent_repository.load(workspace_id, agent_id).lifecycle_state
            if current_state in {"initialized", "running", "blocked"}:
                agent = self.lifecycle.transition(workspace_id, agent_id, "failed")
                trace.append({"state": agent.lifecycle_state, "message": "agent failed"})
                self.audit_log.log_agent_transition(
                    workspace_id=workspace_id,
                    role_id=role.id,
                    agent_id=agent_id,
                    task_id=task_id,
                    from_state=current_state,
                    to_state="failed",
                )

            escalation_target = self._resolve_escalation_target(role)
            escalation_result = self.escalation_handler.escalate_task(
                workspace_id=workspace_id,
                task=task,
                role=role,
                agent=self.agent_repository.load(workspace_id, agent_id),
                reason="execution_failure",
                escalation_target=escalation_target,
                details={
                    "error": error_message,
                    "task_type": str(task.inputs.get("task_type")),
                    "agent_id": agent_id,
                },
            )

            trace.append(
                {
                    "state": "escalated" if escalation_result.ok else "escalation_failed",
                    "message": (
                        f"task escalated to {escalation_result.escalation_target}"
                        if escalation_result.ok
                        else f"escalation failed: {escalation_result.error_code}"
                    ),
                }
            )

            self.audit_log.log_trace(
                workspace_id=workspace_id,
                trace_type="agent_trace",
                agent_id=agent_id,
                task_id=task_id,
                stage="execution_failed",
                message=error_message,
                data={
                    "task_type": task.inputs.get("task_type"),
                    "escalation_target": escalation_target,
                    "escalation_ok": escalation_result.ok,
                },
            )

            final_task = self.task_repository.load(workspace_id, task_id)
            final_agent = self.agent_repository.load(workspace_id, agent_id)

            learning_records = self._capture_and_persist_learning(
                workspace_id=workspace_id,
                task=final_task,
                role=role,
            )

            return AgentExecutionResult(
                ok=False,
                workspace_id=workspace_id,
                agent_id=agent_id,
                task_id=task_id,
                agent_state=final_agent.lifecycle_state,
                task_status=final_task.status,
                trace=trace,
                output=final_task.outputs,
                error=error_message,
                mode="failed",
                escalated=escalation_result.ok,
                escalation_target=escalation_result.escalation_target,
                learning_record_ids=[r.id for r in learning_records],
            )

    def _dispatch_execution(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        agent: AgentSpec,
        task: TaskRecord,
        notes: Dict[str, Any],
    ) -> Dict[str, Any]:
        task_type = task.inputs.get("task_type")

        if task_type == "campaign_review":
            run_state = self.campaign_planning_workflow.run(
                workspace=workspace,
                role=role,
                task=task,
                agent=agent,
                binding_id=self._resolve_binding_id(task, agent, default="offers-binding"),
            )
            if run_state.status != "completed":
                raise ValueError(
                    f"campaign_planning_workflow_failed:{run_state.outputs.get('error')}"
                )
            return {
                "mode": "campaign_planning_workflow",
                "output": {
                    "workflow_id": run_state.workflow_id,
                    "workflow_run_id": run_state.id,
                    "workflow_status": run_state.status,
                    "completed_step_ids": list(run_state.completed_step_ids),
                    "workflow_outputs": dict(run_state.outputs),
                    "summary": "Campaign planning workflow completed successfully.",
                    "notes": notes,
                },
            }

        return {
            "mode": "basic_task_execution",
            "output": self._build_basic_result_payload(
                agent=agent,
                task=task,
                notes=notes,
            ),
        }

    def _build_basic_result_payload(
        self,
        *,
        agent: AgentSpec,
        task: TaskRecord,
        notes: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "summary": f"Completed task for role {agent.role}: {task.objective}",
            "agent_id": agent.id,
            "role": agent.role,
            "objective": task.objective,
            "used_containers": list(agent.allowed_containers),
            "allowed_skills": list(agent.allowed_skills),
            "notes": notes,
        }

    def _capture_and_persist_learning(
        self,
        *,
        workspace_id: str,
        task: TaskRecord,
        role: RoleSpec,
    ) -> List[LearningRecord]:
        business_area = self._resolve_business_area(role)
        return self.learning_service.capture_and_save_from_task(
            workspace_id=workspace_id,
            task=task,
            business_area=business_area,
        )

    def _resolve_binding_id(
        self,
        task: TaskRecord,
        agent: AgentSpec,
        *,
        default: str,
    ) -> str:
        linked = task.linked_containers or []
        if linked:
            return str(linked[0])

        allowed = agent.allowed_containers or []
        if allowed:
            return str(allowed[0])

        return default

    @staticmethod
    def _resolve_escalation_target(role: RoleSpec) -> str:
        if role.escalation_policy_ref and role.escalation_policy_ref.strip():
            return role.escalation_policy_ref
        return "manual_review_queue"

    @staticmethod
    def _resolve_business_area(role: RoleSpec) -> str:
        role_type = (role.role_type or "").upper()
        if role_type == "CMO":
            return "marketing"
        if role_type == "CTO":
            return "engineering"
        if role_type == "CEO":
            return "strategy"
        return "general"

    def _validate_assignment(
        self,
        *,
        agent: AgentSpec,
        task: TaskRecord,
        role: RoleSpec,
        workspace: WorkspaceSpec,
    ) -> None:
        if agent.workspace_id != task.workspace_id:
            raise ValueError("agent_task_workspace_mismatch")

        if workspace.id != task.workspace_id:
            raise ValueError("workspace_task_mismatch")

        if task.assigned_agent_id and task.assigned_agent_id != agent.id:
            raise ValueError("task_assigned_to_different_agent")

        if task.owned_by_role != role.id:
            raise ValueError("agent_task_role_ownership_mismatch")

        if agent.parent_role_id != role.id:
            raise ValueError("agent_parent_role_mismatch")