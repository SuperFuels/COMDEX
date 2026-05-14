from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from backend.modules.aion.runtime.contracts.model_routing import RoutingRequest, TaskType
from backend.modules.aion.runtime.services.model_router import ModelRouter
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.skills import SkillRunRequest
from backend.modules.aion_business.contracts.workflows import (
    WorkflowRunState,
    WorkflowSpec,
    WorkflowStep,
)
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.audit_log import AuditLog
from backend.modules.aion_business.runtime.learning_service import LearningService
from backend.modules.aion_business.runtime.skill_runner import SkillRunner
from backend.modules.aion_business.skills.draft_content import DraftContentSkill
from backend.modules.aion_business.skills.produce_report import ProduceReportSkill
from backend.modules.aion_business.workflows.review_queue import ReviewQueueWorkflow


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WeeklyFounderReviewWorkflow:
    """
    Weekly founder review workflow.

    v2 path:
    1. load workspace learning
    2. run review queue workflow and consume its snapshot
    3. produce structured founder review report
    4. optionally draft a founder-facing summary

    This version reuses ReviewQueueWorkflow as the queue substrate and adds
    founder-level synthesis on top.
    """

    def __init__(
        self,
        *,
        learning_service: Optional[LearningService] = None,
        review_queue_workflow: Optional[ReviewQueueWorkflow] = None,
        skill_runner: Optional[SkillRunner] = None,
        audit_log: Optional[AuditLog] = None,
        model_router: Optional[ModelRouter] = None,
    ):
        self.learning_service = learning_service or LearningService()
        self.review_queue_workflow = review_queue_workflow or ReviewQueueWorkflow()
        self.skill_runner = skill_runner or SkillRunner(
            [
                ProduceReportSkill(),
                DraftContentSkill(),
            ]
        )
        self.audit_log = audit_log or AuditLog()
        self.model_router = model_router or ModelRouter()

    @staticmethod
    def build_spec(workspace_id: str, owner_role: str = "ceo-core") -> WorkflowSpec:
        return WorkflowSpec(
            id="weekly-founder-review",
            workspace_id=workspace_id,
            name="Weekly Founder Review",
            owner_role=owner_role,
            trigger="manual",
            state_model="resumable",
            success_criteria=[
                "workspace learning loaded",
                "review queue snapshot loaded",
                "founder review report produced",
                "founder summary drafted",
            ],
            steps=[
                WorkflowStep(
                    id="load-learning",
                    step_type="retrieval",
                    name="Load workspace learning",
                    success_criteria=["learning records loaded"],
                ),
                WorkflowStep(
                    id="load-review-queue",
                    step_type="review",
                    name="Load review queue snapshot",
                    success_criteria=["review queue snapshot loaded"],
                ),
                WorkflowStep(
                    id="produce-review-report",
                    step_type="skill_execution",
                    name="Produce founder review report",
                    success_criteria=["founder report produced"],
                ),
                WorkflowStep(
                    id="draft-founder-summary",
                    step_type="skill_execution",
                    name="Draft founder summary",
                    success_criteria=["founder summary drafted"],
                ),
            ],
        )

    def run(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        days_back: int = 7,
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
            learning_payload = self._load_learning_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                run_state=run_state,
                days_back=days_back,
            )

            review_queue_payload = self._load_review_queue_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                run_state=run_state,
                days_back=days_back,
                include_draft=False,
            )

            report_result = self._run_report_step(
                workspace=workspace,
                workflow=workflow,
                role=role,
                run_state=run_state,
                learning_payload=learning_payload,
                review_queue_payload=review_queue_payload,
                days_back=days_back,
            )

            run_state.outputs["learning_snapshot"] = learning_payload
            run_state.outputs["review_queue_snapshot"] = review_queue_payload
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
                    "title": f"{workspace.name} Founder Summary Draft",
                    "draft": "",
                    "provider": None,
                    "model": None,
                    "usage": {},
                    "fallback_used": False,
                    "policy_id": None,
                    "route": None,
                    "route_reason": None,
                    "task_type": None,
                    "metadata": {},
                }
                run_state.completed_step_ids.append("draft-founder-summary")

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
                message="Weekly founder review workflow completed",
                data={"run_id": run_state.id},
            )

            self.audit_log.log_event(
                workspace_id=workspace.id,
                event_type="workflow_completed",
                role_id=role.id,
                workflow_id=workflow.id,
                summary="Weekly founder review workflow completed",
                payload={"run_id": run_state.id},
                tags=["workflow", "weekly_founder_review", "completed"],
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
                summary="Weekly founder review workflow failed",
                payload={
                    "run_id": run_state.id,
                    "failed_step_id": run_state.failed_step_id,
                    "error": run_state.outputs["error"],
                },
                tags=["workflow", "weekly_founder_review", "failed"],
            )

            return run_state

    def _load_learning_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        run_state: WorkflowRunState,
        days_back: int,
    ) -> Dict:
        run_state.current_step_id = "load-learning"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="load-learning",
            message="Loading workspace learning",
            data={"days_back": days_back},
        )

        records = self.learning_service.list_workspace_learning(workspace_id=workspace.id)
        filtered = self._filter_recent_learning(records, days_back=days_back)

        payload = {
            "count": len(filtered),
            "by_signal_type": self._count_learning_by_signal(filtered),
            "records_preview": [
                {
                    "id": r.id,
                    "signal_type": r.signal_type,
                    "business_area": r.business_area,
                    "summary": r.summary,
                    "confidence": r.confidence,
                    "created_at": r.created_at,
                }
                for r in filtered[:10]
            ],
        }

        run_state.completed_step_ids.append("load-learning")
        return payload

    def _load_review_queue_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        run_state: WorkflowRunState,
        days_back: int,
        include_draft: bool,
    ) -> Dict:
        run_state.current_step_id = "load-review-queue"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="load-review-queue",
            message="Running review queue workflow for founder review",
            data={"days_back": days_back},
        )

        queue_run = self.review_queue_workflow.run(
            workspace=workspace,
            role=role,
            days_back=days_back,
            include_draft=include_draft,
        )
        if queue_run.status != "completed":
            raise ValueError(f"review_queue_failed:{queue_run.outputs.get('error')}")

        payload = {
            "workflow_id": queue_run.workflow_id,
            "workflow_run_id": queue_run.id,
            "status": queue_run.status,
            "escalation_snapshot": queue_run.outputs.get("escalation_snapshot", {}),
            "target_groups": queue_run.outputs.get("target_groups", {}),
            "role_groups": queue_run.outputs.get("role_groups", {}),
            "produce_report": queue_run.outputs.get("produce_report", {}),
            "draft_content": queue_run.outputs.get("draft_content", {}),
        }

        run_state.completed_step_ids.append("load-review-queue")
        return payload

    def _run_report_step(
        self,
        *,
        workspace: WorkspaceSpec,
        workflow: WorkflowSpec,
        role: RoleSpec,
        run_state: WorkflowRunState,
        learning_payload: Dict,
        review_queue_payload: Dict,
        days_back: int,
    ):
        run_state.current_step_id = "produce-review-report"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="produce-review-report",
            message="Producing founder review report",
            data={"days_back": days_back},
        )

        queue_escalation = review_queue_payload.get("escalation_snapshot", {})
        queue_targets = review_queue_payload.get("target_groups", {})
        queue_roles = review_queue_payload.get("role_groups", {})

        source_data = {
            "workspace_name": workspace.name,
            "business_type": workspace.business_type,
            "review_window_days": days_back,
            "learning_count": learning_payload["count"],
            "learning_by_signal_type": learning_payload["by_signal_type"],
            "learning_preview": learning_payload["records_preview"],
            "review_queue_workflow_id": review_queue_payload.get("workflow_id"),
            "review_queue_workflow_run_id": review_queue_payload.get("workflow_run_id"),
            "escalation_count": queue_escalation.get("count", 0),
            "target_group_count": queue_targets.get("count", 0),
            "role_group_count": queue_roles.get("count", 0),
            "escalation_preview": queue_escalation.get("tasks_preview", []),
            "target_groups": queue_targets.get("groups", {}),
            "role_groups": queue_roles.get("groups", {}),
        }

        result = self.skill_runner.run(
            SkillRunRequest(
                skill_id="produce_report",
                agent_id=f"{role.id}::weekly_founder_review",
                task_id=run_state.id,
                objective=f"Produce weekly founder review for {workspace.name}",
                input_payload={
                    "report_type": "founder_review_report",
                    "title": f"{workspace.name} Weekly Founder Review",
                    "source_data": source_data,
                    "metadata": {
                        "workspace_id": workspace.id,
                        "role_id": role.id,
                        "workflow_id": workflow.id,
                        "workflow_run_id": run_state.id,
                        "review_queue_workflow_id": review_queue_payload.get("workflow_id"),
                        "review_queue_workflow_run_id": review_queue_payload.get("workflow_run_id"),
                    },
                },
                allowed_tools=[],
                allowed_containers=[],
                trace_required=True,
            )
        )
        if not result.ok:
            raise ValueError(f"produce_report_failed:{result.error_code}")

        run_state.completed_step_ids.append("produce-review-report")
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
        run_state.current_step_id = "draft-founder-summary"
        run_state.updated_at = utc_now_iso()

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="draft-founder-summary",
            message="Drafting founder summary via routed local cognition",
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
            f"Write a concise founder-facing weekly review summary for {workspace.name}.\n\n"
            f"Business type: {workspace.business_type}\n"
            f"Review window: last {days_back} days\n"
            f"Report summary: {summary}\n"
            f"Highlights:\n"
            f"{chr(10).join(highlight_lines) if highlight_lines else '- None'}\n\n"
            f"Keep it brief, operational, and decision-focused."
        )

        routing_request = RoutingRequest(
            task_type=TaskType.SUMMARIZE,
            prompt=prompt,
            system="You are a concise chief of staff writing a weekly founder summary.",
            prefers_local=True,
            allow_cloud_fallback=False,
            requires_human_approval=False,
            risk_level="low",
            metadata={
                "max_sentences": 8,
                "workspace_id": workspace.id,
                "workspace_name": workspace.name,
                "role_id": role.id,
                "workflow_id": workflow.id,
                "workflow_run_id": run_state.id,
            },
        )

        router_result = self.model_router.run(routing_request)

        if router_result.decision.route.value != "local_llm":
            raise ValueError(
                f"founder_summary_not_local:{router_result.decision.route.value}"
            )

        draft_text = (router_result.response_text or "").strip()
        if not draft_text:
            raise ValueError("founder_summary_empty")

        output_payload = {
            "title": f"{workspace.name} Founder Summary",
            "draft": draft_text,
            "provider": router_result.raw.get("provider"),
            "model": router_result.raw.get("model"),
            "usage": {},
            "fallback_used": False,
            "policy_id": None,
            "route": router_result.decision.route.value,
            "route_reason": router_result.decision.reason,
            "task_type": router_result.raw.get("task_type"),
            "metadata": router_result.raw.get("metadata", {}),
        }

        self.audit_log.log_trace(
            workspace_id=workspace.id,
            trace_type="workflow_trace",
            workflow_id=workflow.id,
            role_id=role.id,
            stage="draft-founder-summary-completed",
            message="Founder summary drafted via local model router",
            data={
                "run_id": run_state.id,
                "route": router_result.decision.route.value,
                "provider": router_result.raw.get("provider"),
                "model": router_result.raw.get("model"),
            },
        )

        run_state.completed_step_ids.append("draft-founder-summary")

        class _DraftStepResult:
            def __init__(self, output_payload):
                self.ok = True
                self.output_payload = output_payload

        return _DraftStepResult(output_payload)

    @staticmethod
    def _count_learning_by_signal(records) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for record in records:
            counts[record.signal_type] = counts.get(record.signal_type, 0) + 1
        return counts

    @staticmethod
    def _filter_recent_learning(records, *, days_back: int):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        out = []
        for record in records:
            try:
                created = datetime.fromisoformat(record.created_at.replace("Z", "+00:00"))
            except Exception:
                out.append(record)
                continue
            if created >= cutoff:
                out.append(record)
        return out