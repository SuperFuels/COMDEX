from __future__ import annotations

from typing import Any, Dict

from backend.modules.aion_agents.contracts.trigger_definition import TriggerDefinition
from backend.modules.aion_agents.contracts.workflow_run import WorkflowRun
from backend.modules.aion_agents.runtime.trigger_definition_repository import (
    TriggerDefinitionRepository,
)
from backend.modules.aion_agents.runtime.workflow_definition_repository import (
    WorkflowDefinitionRepository,
)
from backend.modules.aion_agents.runtime.workflow_execution_runtime import (
    WorkflowExecutionRuntime,
)


class ManualTriggerService:
    """
    Simple manual launch path.

    This is the first clean entry point for:
    - boardroom "run this workflow"
    - agent inspector "launch now"
    - simple testing of trigger/workflow wiring

    Important:
    - repositories/runtime are injected from the composition root
    - this avoids silently writing to a different storage base_dir
    """

    def __init__(
        self,
        *,
        trigger_repository: TriggerDefinitionRepository | None = None,
        workflow_repository: WorkflowDefinitionRepository,
        execution_runtime: WorkflowExecutionRuntime,
    ) -> None:
        self.trigger_repository = trigger_repository
        self.workflow_repository = workflow_repository
        self.execution_runtime = execution_runtime

    def launch_workflow(
        self,
        *,
        workspace_id: str,
        workflow_id: str,
        launched_by: str = "manual",
        agent_id: str | None = None,
        payload: Dict[str, Any] | None = None,
        require_approval: bool | None = None,
    ) -> WorkflowRun:
        workflow = self.workflow_repository.load(workspace_id, workflow_id)

        launch_payload = {
            **dict(payload or {}),
            "launch_mode": "manual",
            "launched_by": launched_by,
            "agent_id": agent_id,
        }

        if require_approval is True:
            workflow.execution_mode = "draft_with_approval"

        return self.execution_runtime.launch_workflow(
            workflow=workflow,
            agent=None,
            trigger_id=None,
            trigger_event_type="manual",
            input_payload=launch_payload,
            context=launch_payload,
        )

    def launch_trigger(
        self,
        *,
        workspace_id: str,
        trigger_id: str,
        launched_by: str = "manual",
        payload: Dict[str, Any] | None = None,
    ) -> WorkflowRun:
        if self.trigger_repository is None:
            raise ValueError("Trigger repository is not configured for trigger launches")

        trigger = self.trigger_repository.load(workspace_id, trigger_id)
        return self.launch_from_trigger(
            trigger=trigger,
            launched_by=launched_by,
            payload=payload,
        )

    def launch_from_trigger(
        self,
        *,
        trigger: TriggerDefinition,
        launched_by: str = "manual",
        payload: Dict[str, Any] | None = None,
    ) -> WorkflowRun:
        trigger_id = getattr(trigger, "trigger_id", None) or getattr(trigger, "id", None)
        trigger_type = getattr(trigger, "trigger_type", None) or getattr(trigger, "type", None)
        workflow_id = getattr(trigger, "workflow_id", None) or getattr(
            trigger,
            "workflow_definition_id",
            None,
        )

        if not workflow_id:
            raise ValueError("Trigger is missing workflow reference")

        workflow = self.workflow_repository.load(trigger.workspace_id, workflow_id)

        launch_payload = {
            **dict(payload or {}),
            "launch_mode": "manual_trigger",
            "launched_by": launched_by,
            "trigger_id": trigger_id,
            "trigger_type": trigger_type,
        }

        return self.execution_runtime.launch_workflow(
            workflow=workflow,
            agent=None,
            trigger_id=trigger_id,
            trigger_event_type=trigger_type or "manual",
            input_payload=launch_payload,
            context=launch_payload,
        )