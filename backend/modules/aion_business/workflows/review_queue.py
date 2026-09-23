from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Dict, Optional

from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.skills import SkillRunRequest
from backend.modules.aion_business.contracts.workflows import (
    WorkflowRunState,
    WorkflowSpec,
    WorkflowStep,
)
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.audit_log import AuditLog
from backend.modules.aion_business.runtime.review_queue_service import ReviewQueueService
from backend.modules.aion_business.runtime.skill_runner import SkillRunner
from backend.modules.aion_business.skills.draft_content import DraftContentSkill
from backend.modules.aion_business.skills.produce_report import ProduceReportSkill


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ReviewQueueWorkflow:
    """
    Review queue workflow.

    v2 path:
    1. load escalated tasks snapshot
    2. group by escalation target
    3. group by owning role
    4. produce structured review queue report
    5. optionally draft a short queue summary

    Queue construction logic lives in ReviewQueueService so it can be reused by:
    - founder review
    - workflow APIs
    - future UI surfaces
    """

    def __init__(
        self,
        *,
        review_queue_service: Optional[ReviewQueueService] = None,
        skill_runner: Optional[SkillRunner] = None,
        audit_log: Optional[AuditLog] = None,
    ):
        self.review_queue_service = review_queue_service or ReviewQueueService()
        self.skill_runner = skill_runner or SkillRunner(
            [
                ProduceReportSkill(),
                DraftContentSkill(),
            ]
        )
        self.audit_log = audit_log or AuditLog()

    @staticmethod
    def build_spec(workspace_id: str, owner_role: str = "ceo-core") -> WorkflowSpec:
        return WorkflowSpec(
            id="review-queue",
            workspace_id=workspace_id,
            name="Review Queue",
            owner_role=owner_role,
            trigger="manual",
            state_model="resumable",
            success_criteria=[
                "escalated tasks loaded",
                "queue grouped by target",
                "queue grouped by role",
                "review queue report produced",
                "review queue summary drafted",
            ],
            steps=[
                WorkflowStep(
                    id="load-escalations",
                    step_type="retrieval",
                    name="Load escalated tasks",
                    success_criteria=["escalated tasks loaded"],
                ),
                WorkflowStep(
                    id="group-by-target",
                    step_type="review",
                    name="Group queue by escalation target",
                    success_criteria=["queue grouped by target"],
                ),
                WorkflowStep(
                    id="group-by-role",
                    step_type="review",
                    name="Group queue by role",
                    success_criteria=["queue grouped by role"],
                ),
                WorkflowStep(
                    id="produce-queue-report",
                    step_type="skill_execution",
                    name="Produce review queue report",
                    success_criteria=["queue report produced"],
                ),
                WorkflowStep(
                    id="draft-queue-summary",
                    step_type="skill_execution",
                    name="Draft review queue summary",
                    success_criteria=["queue summary drafted"],
                ),
            ],
        )

    def run(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        days_back: int = 30,
        include_draft: bool = True,
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
                "workspace_id": workspace.id,
                "role_id": role.id,
                "days_back": days_back,
                "include_draft": include_draft,
            },
        )

        try:
            snapshot = self.review_queue_service.build_queue_snapshot(
                workspace_id=workspace.id,
                days_back=days_back,
            )

            escalation_payload = self._load_escalations_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                run_state=run_state,
                days_back=days_back,
                snapshot=snapshot,
            )

            target_payload = self._group_by_target_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                run_state=run_state,
                escalation_payload=escalation_payload,
                snapshot=snapshot,
            )

            role_payload = self._group_by_role_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                run_state=run_state,
                escalation_payload=escalation_payload,
                snapshot=snapshot,
            )

            report_result = self._run_report_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                run_state=run_state,
                escalation_payload=escalation_payload,
                target_payload=target_payload,
                role_payload=role_payload,
                days_back=days_back,
            )

            run_state.outputs["escalation_snapshot"] = escalation_payload
            run_state.outputs["target_groups"] = target_payload
            run_state.outputs["role_groups"] = role_payload
            run_state.outputs["produce_report"] = report_result.output_payload

            if include_draft:
                draft_result = self._run_draft_step(
                    workspace=workspace,
                    workflow=workflow,
                    role=role,
                    run_state=run_state,
                    report_result=report_result,
                    days_back=days_back,
                )
                run_state.outputs["draft_content"] = draft_result.output_payload
            else:
                run_state.outputs["draft_content"] = {
                    "title": f"{workspace.name} Review Queue Summary",
                    "draft": "",
                    "provider": None,
                    "model": None,
                    "usage": {},
                    "fallback_used": False,
                    "policy_id": None,
                }
                run_state.completed_step_ids.append("draft-queue-summary")

            run_state.status = "completed"
            run_state.current_step_id = None
            run_state.completed_at = utc_now_iso()
            run_state.updated_at = utc_now_iso()

            self.audit_log.log_trace(
                workspace_id=workspace.id,
                trace_type="workflow_trace",
                workflow_id=workflow.id,
                role_id=role.id,
                stage="workflow_completed",
                message="Review queue workflow completed",
                data={"run_id": run_state.id},
            )

            self.audit_log.log_event(
                workspace_id=workspace.id,
                event_type="workflow_completed",
                role_id=role.id,
                workflow_id=workflow.id,
                summary="Review queue workflow completed",
                payload={"run_id": run_state.id},
                tags=["workflow", "review_queue", "completed"],
            )

            return run_state

        except Exception as exc:
            run_state.status = "failed"
            run_state.failed_step_id = run_state.current_step_id
            run_state.updated_at = utc_now_iso()
            run_state.outputs["error"] = f"{type(exc).__name__}: {exc}"

            self.audit_log.log_trace(
                workspace_id=workspace.id,
                trace_type="workflow_trace",
                workflow_id=workflow.id,
                role_id=role.id,
                stage="workflow_failed",
                message=f"{type(exc).__name__}: {exc}",
                data={"run_id": run_state.id, "failed_step_id": run_state.failed_step_id},
            )

            self.audit_log.log_event(
                workspace_id=workspace.id,
                event_type="workflow_failed",
                role_id=role.id,
                workflow_id=workflow.id,
                summary=f"Review queue workflow failed: {type(exc).__name__}",
                payload={
                    "run_id": run_state.id,
                    "failed_step_id": run_state.failed_step_id,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                tags=["workflow", "review_queue", "failed"],
            )

            return run_state

    def _load_escalations_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        run_state: WorkflowRunState,
        days_back: int,
        snapshot: Dict,
    ) -> Dict:
        run_state.current_step_id = "load-escalations"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="load-escalations",
            message="Loading escalated tasks for review queue",
            data={"days_back": days_back},
        )

        payload = snapshot["escalation_snapshot"]

        run_state.completed_step_ids.append("load-escalations")
        return payload

    def _group_by_target_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        run_state: WorkflowRunState,
        escalation_payload: Dict,
        snapshot: Dict,
    ) -> Dict:
        run_state.current_step_id = "group-by-target"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="group-by-target",
            message="Grouping queue by escalation target",
            data={"task_count": escalation_payload["count"]},
        )

        payload = snapshot["target_groups"]

        run_state.completed_step_ids.append("group-by-target")
        return payload

    def _group_by_role_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        run_state: WorkflowRunState,
        escalation_payload: Dict,
        snapshot: Dict,
    ) -> Dict:
        run_state.current_step_id = "group-by-role"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="group-by-role",
            message="Grouping queue by owning role",
            data={"task_count": escalation_payload["count"]},
        )

        payload = snapshot["role_groups"]

        run_state.completed_step_ids.append("group-by-role")
        return payload

    def _run_report_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        run_state: WorkflowRunState,
        escalation_payload: Dict,
        target_payload: Dict,
        role_payload: Dict,
        days_back: int,
    ):
        run_state.current_step_id = "produce-queue-report"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="produce-queue-report",
            message="Producing review queue report",
            data={"days_back": days_back},
        )

        source_data = {
            "workspace_name": workspace.name,
            "business_type": workspace.business_type,
            "review_window_days": days_back,
            "escalation_count": escalation_payload["count"],
            "target_group_count": target_payload["count"],
            "role_group_count": role_payload["count"],
            "escalation_preview": escalation_payload["tasks_preview"],
            "target_groups": target_payload["groups"],
            "role_groups": role_payload["groups"],
        }

        result = self.skill_runner.run(
            SkillRunRequest(
                skill_id="produce_report",
                agent_id=f"{role.id}::review_queue",
                task_id=run_state.id,
                objective=f"Produce review queue report for {workspace.name}",
                input_payload={
                    "report_type": "review_queue_report",
                    "title": f"{workspace.name} Review Queue",
                    "source_data": source_data,
                    "metadata": {
                        "workspace_id": workspace.id,
                        "role_id": role.id,
                        "workflow_id": workflow.id,
                        "workflow_run_id": run_state.id,
                    },
                },
                allowed_tools=[],
                allowed_containers=[],
                trace_required=True,
            )
        )
        if not result.ok:
            raise ValueError(f"produce_report_failed:{result.error_code}")

        run_state.completed_step_ids.append("produce-queue-report")
        return result

    def _run_draft_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        run_state: WorkflowRunState,
        report_result,
        days_back: int,
    ):
        run_state.current_step_id = "draft-queue-summary"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="draft-queue-summary",
            message="Drafting review queue summary",
            data={"days_back": days_back},
        )

        report = report_result.output_payload.get("report", {})
        summary = report.get("summary", "")
        highlights = report.get("highlights", [])

        highlight_lines = []
        for item in highlights[:6]:
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
            f"Write a concise review queue summary for {workspace.name}.\n\n"
            f"Business type: {workspace.business_type}\n"
            f"Review window: last {days_back} days\n"
            f"Report summary: {summary}\n"
            f"Highlights:\n"
            f"{chr(10).join(highlight_lines) if highlight_lines else '- None'}\n\n"
            f"Keep it brief, operational, and prioritised."
        )

        result = self.skill_runner.run(
            SkillRunRequest(
                skill_id="draft_content",
                agent_id=f"{role.id}::review_queue",
                task_id=run_state.id,
                objective=f"Draft review queue summary for {workspace.name}",
                input_payload={
                    "title": f"{workspace.name} Review Queue Summary",
                    "prompt": prompt,
                    "system_prompt": "You are a concise operations lead writing a review queue summary.",
                    "provider": "openai",
                    "model_policy_ref": role.model_policy_ref,
                    "role_type": role.role_type,
                    "capability": "drafting",
                    "metadata": {
                        "workspace_id": workspace.id,
                        "workspace_name": workspace.name,
                        "role_id": role.id,
                        "workflow_id": workflow.id,
                        "workflow_run_id": run_state.id,
                    },
                },
                allowed_tools=[],
                allowed_containers=[],
                trace_required=True,
            )
        )
        if not result.ok:
            raise ValueError(f"draft_content_failed:{result.error_code}")

        run_state.completed_step_ids.append("draft-queue-summary")
        return result