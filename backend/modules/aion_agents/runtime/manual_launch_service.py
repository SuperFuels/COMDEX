from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.aion_agents.contracts.workflow_run import WorkflowRun
from backend.modules.aion_agents.runtime.agent_definition_repository import (
    AgentDefinitionRepository,
)
from backend.modules.aion_agents.runtime.manual_trigger_service import ManualTriggerService
from backend.modules.aion_agents.runtime.workflow_definition_repository import (
    WorkflowDefinitionRepository,
)
from backend.modules.aion_agents.runtime.workflow_execution_runtime import (
    WorkflowExecutionRuntime,
)


class ManualLaunchService:
    """
    Thin compatibility layer for manual workflow launches from the local node /
    boardroom surface.

    This wraps ManualTriggerService but exposes the method shape expected by
    LocalNodeRuntime:
      - launch(...)
      - workflow_definition_id
      - agent_definition_id
      - context
    """

    def __init__(
        self,
        *,
        workflow_execution_runtime: WorkflowExecutionRuntime,
        workflow_definition_repository: WorkflowDefinitionRepository,
        agent_definition_repository: AgentDefinitionRepository,
    ) -> None:
        self.workflow_execution_runtime = workflow_execution_runtime
        self.workflow_definition_repository = workflow_definition_repository
        self.agent_definition_repository = agent_definition_repository

        self._manual_trigger_service = ManualTriggerService(
            trigger_repository=None,  # not needed for direct workflow launches
            workflow_repository=workflow_definition_repository,
            execution_runtime=workflow_execution_runtime,
        )

    def launch(
        self,
        *,
        workspace_id: str,
        workflow_definition_id: str,
        agent_definition_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        launched_by: str = "manual",
        require_approval: Optional[bool] = None,
    ) -> Dict[str, Any]:
        agent = None
        if agent_definition_id:
            agent = self.agent_definition_repository.find_one(
                workspace_id,
                agent_definition_id,
            )

        run: WorkflowRun = self._manual_trigger_service.launch_workflow(
            workspace_id=workspace_id,
            workflow_id=workflow_definition_id,
            launched_by=launched_by,
            agent_id=agent_definition_id,
            payload=context or {},
            require_approval=require_approval,
        )

        return {
            "ok": True,
            "run_id": run.id,
            "workflow_id": run.workflow_id,
            "workflow_name": getattr(run, "workflow_name", workflow_definition_id),
            "operator_id": getattr(run, "operator_id", None) or agent_definition_id,
            "agent_definition_id": agent_definition_id,
            "agent_name": getattr(agent, "name", None) if agent else None,
            "status": run.status,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }