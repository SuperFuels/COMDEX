from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.audit import AuditEvent
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.skills import SkillRunRequest
from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.contracts.workflows import (
    WorkflowRunState,
    WorkflowSpec,
    WorkflowStep,
)
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.audit_log import AuditLog
from backend.modules.aion_business.runtime.agent_repository import AgentRepository
from backend.modules.aion_business.runtime.skill_runner import SkillRunner
from backend.modules.aion_business.runtime.task_record_repository import TaskRecordRepository
from backend.modules.aion_business.skills.draft_content import DraftContentSkill
from backend.modules.aion_business.skills.produce_report import ProduceReportSkill
from backend.modules.aion_business.skills.read_container import ReadContainerSkill
from backend.modules.aion_business.skills.summarize_docs import SummarizeDocsSkill


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class CampaignPlanningWorkflow:
    def __init__(
        self,
        *,
        skill_runner: Optional[SkillRunner] = None,
        audit_log: Optional[AuditLog] = None,
        task_repository: Optional[TaskRecordRepository] = None,
        agent_repository: Optional[AgentRepository] = None,
    ):
        self.skill_runner = skill_runner or SkillRunner(
            [
                ReadContainerSkill(),
                SummarizeDocsSkill(),
                ProduceReportSkill(),
                DraftContentSkill(),
            ]
        )
        self.audit_log = audit_log or AuditLog()
        self.task_repository = task_repository or TaskRecordRepository()
        self.agent_repository = agent_repository or AgentRepository()

    @staticmethod
    def build_spec(workspace_id: str, owner_role: str = "cmo-core") -> WorkflowSpec:
        return WorkflowSpec(
            id="campaign-planning",
            workspace_id=workspace_id,
            name="Campaign Planning",
            owner_role=owner_role,
            trigger="manual",
            state_model="resumable",
            success_criteria=[
                "offers container read",
                "offers summarized",
                "campaign report produced",
                "campaign copy drafted",
            ],
            steps=[
                WorkflowStep(
                    id="read-offers",
                    step_type="retrieval",
                    name="Read offers container",
                    success_criteria=["offers container loaded"],
                ),
                WorkflowStep(
                    id="summarize-offers",
                    step_type="skill_execution",
                    name="Summarize offers container",
                    success_criteria=["offers summary produced"],
                ),
                WorkflowStep(
                    id="produce-report",
                    step_type="skill_execution",
                    name="Produce campaign context report",
                    success_criteria=["report produced"],
                ),
                WorkflowStep(
                    id="draft-campaign-copy",
                    step_type="skill_execution",
                    name="Draft campaign copy",
                    success_criteria=["campaign copy drafted"],
                ),
            ],
        )

    def run(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        task: TaskRecord,
        agent: AgentSpec,
        binding_id: str = "offers-binding",
    ) -> WorkflowRunState:
        workflow = self.build_spec(workspace.id, owner_role=role.id)

        run_state = WorkflowRunState(
            id=f"run-{secrets.token_hex(6)}",
            workflow_id=workflow.id,
            workspace_id=workspace.id,
            status="running",
            started_at=utc_now_iso(),
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
            context={
                "binding_id": binding_id,
                "task_id": task.id,
                "agent_id": agent.id,
                "role_id": role.id,
            },
        )

        try:
            read_result = self._run_read_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                task=task,
                agent=agent,
                run_state=run_state,
                binding_id=binding_id,
            )

            summarize_result = self._run_summarize_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                task=task,
                agent=agent,
                run_state=run_state,
                binding_id=binding_id,
            )

            report_result = self._run_report_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                task=task,
                agent=agent,
                run_state=run_state,
                binding_id=binding_id,
                summarize_result=summarize_result,
            )

            draft_result = self._run_draft_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                task=task,
                agent=agent,
                run_state=run_state,
                binding_id=binding_id,
                report_result=report_result,
            )

            run_state.outputs["read_container"] = read_result.output_payload
            run_state.outputs["summarize_docs"] = summarize_result.output_payload
            run_state.outputs["produce_report"] = report_result.output_payload
            run_state.outputs["draft_content"] = draft_result.output_payload

            run_state.status = "completed"
            run_state.current_step_id = None
            run_state.completed_at = utc_now_iso()
            run_state.updated_at = utc_now_iso()

            self._persist_task_workflow_output(task=task, run_state=run_state)

            self.audit_log.append_event(
                self._build_workflow_completed_event(
                    workspace_id=workspace.id,
                    workflow_id=workflow.id,
                    role_id=role.id,
                    agent_id=agent.id,
                    task_id=task.id,
                    run_id=run_state.id,
                )
            )

            return run_state

        except Exception as exc:
            run_state.status = "failed"
            run_state.failed_step_id = run_state.current_step_id
            run_state.updated_at = utc_now_iso()
            run_state.outputs["error"] = f"{type(exc).__name__}: {exc}"

            self._persist_task_workflow_output(task=task, run_state=run_state)

            self.audit_log.log_trace(
                workspace_id=workspace.id,
                trace_type="workflow_trace",
                workflow_id=workflow.id,
                task_id=task.id,
                agent_id=agent.id,
                stage="workflow_failed",
                message=f"{type(exc).__name__}: {exc}",
                data={"run_id": run_state.id, "failed_step_id": run_state.failed_step_id},
            )

            return run_state

    def _run_read_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        task: TaskRecord,
        agent: AgentSpec,
        run_state: WorkflowRunState,
        binding_id: str,
    ):
        run_state.current_step_id = "read-offers"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            task_id=task.id,
            agent_id=agent.id,
            stage="read-offers",
            message="Starting read_container step",
            data={"binding_id": binding_id},
        )

        result = self.skill_runner.run(
            SkillRunRequest(
                skill_id="read_container",
                agent_id=agent.id,
                task_id=task.id,
                objective=task.objective,
                input_payload={"binding_id": binding_id},
                allowed_tools=list(agent.allowed_tools),
                allowed_containers=list(agent.allowed_containers),
                trace_required=True,
            )
        )
        if not result.ok:
            raise ValueError(f"read_container_failed:{result.error_code}")

        run_state.completed_step_ids.append("read-offers")
        return result

    def _run_summarize_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        task: TaskRecord,
        agent: AgentSpec,
        run_state: WorkflowRunState,
        binding_id: str,
    ):
        run_state.current_step_id = "summarize-offers"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            task_id=task.id,
            agent_id=agent.id,
            stage="summarize-offers",
            message="Starting summarize_docs step",
            data={"binding_id": binding_id},
        )

        result = self.skill_runner.run(
            SkillRunRequest(
                skill_id="summarize_docs",
                agent_id=agent.id,
                task_id=task.id,
                objective=task.objective,
                input_payload={
                    "binding_id": binding_id,
                    "workspace": workspace,
                    "role": role,
                    "agent": agent,
                    "task": task,
                },
                allowed_tools=list(agent.allowed_tools),
                allowed_containers=list(agent.allowed_containers),
                trace_required=True,
            )
        )
        if not result.ok:
            raise ValueError(f"summarize_docs_failed:{result.error_code}")

        run_state.completed_step_ids.append("summarize-offers")
        return result

    def _run_report_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        task: TaskRecord,
        agent: AgentSpec,
        run_state: WorkflowRunState,
        binding_id: str,
        summarize_result,
    ):
        run_state.current_step_id = "produce-report"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            task_id=task.id,
            agent_id=agent.id,
            stage="produce-report",
            message="Starting produce_report step",
            data={"binding_id": binding_id},
        )

        result = self.skill_runner.run(
            SkillRunRequest(
                skill_id="produce_report",
                agent_id=agent.id,
                task_id=task.id,
                objective=task.objective,
                input_payload={
                    "report_type": "campaign_context_report",
                    "title": f"{workspace.name} Campaign Context Review",
                    "source_data": summarize_result.output_payload.get("summary", {}),
                    "metadata": {
                        "workspace_id": workspace.id,
                        "role_id": role.id,
                        "task_id": task.id,
                        "agent_id": agent.id,
                        "binding_id": binding_id,
                    },
                },
                allowed_tools=list(agent.allowed_tools),
                allowed_containers=list(agent.allowed_containers),
                trace_required=True,
            )
        )
        if not result.ok:
            raise ValueError(f"produce_report_failed:{result.error_code}")

        run_state.completed_step_ids.append("produce-report")
        return result

    def _run_draft_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        task: TaskRecord,
        agent: AgentSpec,
        run_state: WorkflowRunState,
        binding_id: str,
        report_result,
    ):
        run_state.current_step_id = "draft-campaign-copy"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            task_id=task.id,
            agent_id=agent.id,
            stage="draft-campaign-copy",
            message="Starting draft_content step",
            data={"binding_id": binding_id},
        )

        report = report_result.output_payload.get("report", {})
        summary = report.get("summary", "")
        highlights = report.get("highlights", [])

        highlight_lines = []
        for item in highlights[:5]:
            if isinstance(item, dict):
                if "text" in item:
                    highlight_lines.append(f"- {item['text']}")
                elif "key" in item and "value" in item:
                    highlight_lines.append(f"- {item['key']}: {item['value']}")
                elif "key" in item and "count" in item:
                    highlight_lines.append(f"- {item['key']} count: {item['count']}")
                else:
                    highlight_lines.append(f"- {item}")
            else:
                highlight_lines.append(f"- {item}")

        prompt = (
            f"Create one short broadband campaign line for {workspace.name}.\n\n"
            f"Business type: {workspace.business_type}\n"
            f"Objective: {task.objective}\n"
            f"Report summary: {summary}\n"
            f"Highlights:\n"
            f"{chr(10).join(highlight_lines) if highlight_lines else '- None'}"
        )

        result = self.skill_runner.run(
            SkillRunRequest(
                skill_id="draft_content",
                agent_id=agent.id,
                task_id=task.id,
                objective=task.objective,
                input_payload={
                    "title": f"{workspace.name} Campaign Draft",
                    "prompt": prompt,
                    "system_prompt": "You are a concise telecoms marketing copywriter. Write one short strong line.",
                    "provider": "openai",
                    "model_policy_ref": role.model_policy_ref,
                    "metadata": {
                        "workspace_id": workspace.id,
                        "workspace_name": workspace.name,
                        "role_id": role.id,
                        "task_id": task.id,
                        "agent_id": agent.id,
                        "binding_id": binding_id,
                        "workflow_id": workflow.id,
                        "workflow_run_id": run_state.id,
                    },
                },
                allowed_tools=list(agent.allowed_tools),
                allowed_containers=list(agent.allowed_containers),
                trace_required=True,
            )
        )
        if not result.ok:
            raise ValueError(f"draft_content_failed:{result.error_code}")

        run_state.completed_step_ids.append("draft-campaign-copy")
        return result

    def _persist_task_workflow_output(
        self,
        *,
        task: TaskRecord,
        run_state: WorkflowRunState,
    ) -> None:
        task.outputs["campaign_planning_workflow"] = run_state.model_dump(mode="json")
        task.updated_at = utc_now_iso()
        self.task_repository.save(task)

    def _build_workflow_completed_event(
        self,
        *,
        workspace_id: str,
        workflow_id: str,
        role_id: str,
        agent_id: str,
        task_id: str,
        run_id: str,
    ) -> AuditEvent:
        return AuditEvent(
            id=f"audit-{secrets.token_hex(8)}",
            workspace_id=workspace_id,
            event_type="workflow_completed",
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            workflow_id=workflow_id,
            summary="Campaign planning workflow completed",
            payload={"run_id": run_id},
            tags=["workflow", "campaign_planning", "completed"],
        )