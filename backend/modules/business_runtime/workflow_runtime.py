from __future__ import annotations

import uuid
from typing import Any, Dict

from .approval_runtime import ApprovalRuntime
from .contracts_workflow import (
    WorkflowDefinition,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStepDefinition,
    WorkflowStepRun,
    WorkflowStepStatus,
)
from .operator_registry import OperatorRegistry
from .workflow_repository import WorkflowRepository


class WorkflowRuntime:
    def __init__(
        self,
        repository: WorkflowRepository | None = None,
        operator_registry: OperatorRegistry | None = None,
        approval_runtime: ApprovalRuntime | None = None,
    ) -> None:
        self.repository = repository or WorkflowRepository()
        self.operator_registry = operator_registry or OperatorRegistry()
        self.approval_runtime = approval_runtime or ApprovalRuntime()

    @staticmethod
    def _step_kind_value(step_kind: Any) -> str:
        return step_kind.value if hasattr(step_kind, "value") else str(step_kind)

    def hydrate_workflow(self, row: WorkflowDefinition | dict) -> WorkflowDefinition:
        if isinstance(row, WorkflowDefinition):
            return row

        payload = dict(row)
        payload["steps"] = [
            step if isinstance(step, WorkflowStepDefinition) else WorkflowStepDefinition(**step)
            for step in payload.get("steps", [])
        ]
        return WorkflowDefinition(**payload)

    def create_run(
        self,
        workflow: WorkflowDefinition | dict,
        trigger_kind: str,
        initial_context: Dict[str, Any] | None = None,
    ) -> WorkflowRun:
        workflow = self.hydrate_workflow(workflow)

        step_runs = [
            WorkflowStepRun(
                id=f"step_run_{uuid.uuid4().hex[:10]}",
                step_id=step.id,
                kind=self._step_kind_value(step.kind),
            )
            for step in workflow.steps
        ]

        run = WorkflowRun(
            id=f"run_{uuid.uuid4().hex[:10]}",
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            operator_id=workflow.operator_id,
            department_key=workflow.department_key,
            trigger_kind=trigger_kind,
            execution_mode=workflow.execution_mode,
            context=initial_context or {},
            step_runs=step_runs,
        )
        self.repository.save_workflow_run(run)
        return run

    def execute_run(self, workflow: WorkflowDefinition | dict, run: WorkflowRun) -> WorkflowRun:
        workflow = self.hydrate_workflow(workflow)

        run.status = WorkflowRunStatus.RUNNING
        run.touch()
        self.repository.save_workflow_run(run)

        for i in range(run.current_step_index, len(workflow.steps)):
            step_def = workflow.steps[i]
            step_run = run.step_runs[i]
            step_kind = self._step_kind_value(step_def.kind)

            run.current_step_index = i
            step_run.status = WorkflowStepStatus.RUNNING
            run.touch()
            step_run.started_at = run.updated_at
            self.repository.save_workflow_run(run)

            if step_kind == "create_brief":
                brief = (
                    run.context.get("brief")
                    or "Create a local marketing content draft for this week."
                )
                run.context["brief"] = brief
                step_run.output = {"brief": brief}
                step_run.status = WorkflowStepStatus.COMPLETED

            elif step_kind == "draft_caption":
                brief = run.context.get("brief") or "Marketing brief"
                draft_caption = f"Draft caption based on: {brief}"
                run.context["draft_caption"] = draft_caption
                step_run.output = {"draft_caption": draft_caption}
                step_run.status = WorkflowStepStatus.COMPLETED

            elif step_kind == "draft_carousel":
                draft_carousel = ["Hook", "Problem", "Solution", "Proof", "CTA"]
                run.context["draft_carousel"] = draft_carousel
                step_run.output = {"draft_carousel": draft_carousel}
                step_run.status = WorkflowStepStatus.COMPLETED

            elif step_kind == "attach_connector_context":
                connector_key = (step_def.config or {}).get("connector_key", "meta_facebook")
                connector_context = {"connector_key": connector_key}
                run.context["connector_context"] = connector_context
                step_run.output = {"connector_context": connector_context}
                step_run.status = WorkflowStepStatus.COMPLETED

            elif step_kind == "request_approval":
                req = self.approval_runtime.create_request(
                    workflow_run_id=run.id,
                    operator_id=run.operator_id,
                    department_key=run.department_key,
                    title="Approve marketing content draft",
                    summary="Review the generated caption and carousel structure.",
                    payload={
                        "brief": run.context.get("brief"),
                        "draft_caption": run.context.get("draft_caption"),
                        "draft_carousel": run.context.get("draft_carousel"),
                        "connector_context": run.context.get("connector_context"),
                    },
                )
                run.approval_request_id = req.id
                run.status = WorkflowRunStatus.WAITING_APPROVAL
                step_run.status = WorkflowStepStatus.WAITING_APPROVAL
                step_run.output = {"approval_request_id": req.id}
                run.touch()
                self.repository.save_workflow_run(run)
                return run

            elif step_kind == "complete_run":
                run.context["result"] = {
                    "draft_caption": run.context.get("draft_caption"),
                    "draft_carousel": run.context.get("draft_carousel"),
                    "connector_context": run.context.get("connector_context"),
                    "status": "ready",
                }
                step_run.output = {"result": run.context["result"]}
                step_run.status = WorkflowStepStatus.COMPLETED

            else:
                step_run.status = WorkflowStepStatus.FAILED
                step_run.error = f"Unsupported step kind: {step_kind}"
                run.status = WorkflowRunStatus.FAILED
                run.failure_reason = step_run.error
                run.touch()
                self.repository.save_workflow_run(run)
                return run

            run.touch()
            step_run.completed_at = run.updated_at
            self.repository.save_workflow_run(run)

        run.status = WorkflowRunStatus.COMPLETED
        run.completed_at = run.updated_at
        self.repository.save_workflow_run(run)
        return run

    def resume_after_approval(
        self,
        workflow: WorkflowDefinition | dict,
        run: WorkflowRun,
        approved: bool,
    ) -> WorkflowRun:
        workflow = self.hydrate_workflow(workflow)

        if not approved:
            run.status = WorkflowRunStatus.FAILED
            run.failure_reason = "Approval rejected"
            run.touch()
            run.completed_at = run.updated_at
            self.repository.save_workflow_run(run)
            return run

        current_index = run.current_step_index
        if current_index < len(run.step_runs):
            run.step_runs[current_index].status = WorkflowStepStatus.COMPLETED
            run.touch()
            run.step_runs[current_index].completed_at = run.updated_at

        run.current_step_index = current_index + 1
        run.status = WorkflowRunStatus.RUNNING
        run.touch()
        self.repository.save_workflow_run(run)
        return self.execute_run(workflow, run)

    def hydrate_run(self, row: dict) -> WorkflowRun:
        payload = dict(row)
        payload["step_runs"] = [
            step if isinstance(step, WorkflowStepRun) else WorkflowStepRun(**step)
            for step in payload.get("step_runs", [])
        ]
        return WorkflowRun(**payload)