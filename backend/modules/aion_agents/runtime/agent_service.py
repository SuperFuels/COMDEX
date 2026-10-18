from __future__ import annotations

from typing import Dict, List

from backend.modules.aion_agents.contracts.agent_definition import AgentDefinition
from backend.modules.aion_agents.contracts.trigger_definition import TriggerDefinition
from backend.modules.aion_agents.contracts.workflow_definition import WorkflowDefinition
from backend.modules.aion_agents.runtime.agent_definition_repository import (
    AgentDefinitionRepository,
)
from backend.modules.aion_agents.runtime.trigger_definition_repository import (
    TriggerDefinitionRepository,
)
from backend.modules.aion_agents.runtime.workflow_definition_repository import (
    WorkflowDefinitionRepository,
)


class AgentService:
    """
    Thin orchestration layer above agent/workflow/trigger repositories.

    Important:
    - repositories are injected from the composition root
    - this avoids silently writing to a different storage base_dir
    """

    def __init__(
        self,
        *,
        agent_repository: AgentDefinitionRepository,
        workflow_repository: WorkflowDefinitionRepository,
        trigger_repository: TriggerDefinitionRepository,
    ) -> None:
        self.agent_repository = agent_repository
        self.workflow_repository = workflow_repository
        self.trigger_repository = trigger_repository

    def save_agent(self, agent: AgentDefinition) -> AgentDefinition:
        return self.agent_repository.save(agent)

    def get_agent(
        self,
        workspace_id: str,
        agent_id: str,
    ) -> AgentDefinition | None:
        return self.agent_repository.find_one(workspace_id, agent_id)

    def list_agents(self, workspace_id: str) -> List[AgentDefinition]:
        return self.agent_repository.list_all(workspace_id)

    def list_active_agents(self, workspace_id: str) -> List[AgentDefinition]:
        return [
            item
            for item in self.agent_repository.list_all(workspace_id)
            if getattr(item, "active", True)
        ]

    def get_workflow(
        self,
        workspace_id: str,
        workflow_id: str,
    ) -> WorkflowDefinition | None:
        return self.workflow_repository.get(workspace_id, workflow_id)

    def list_agent_workflows(
        self,
        workspace_id: str,
        agent_id: str,
    ) -> List[WorkflowDefinition]:
        agent = self.get_agent(workspace_id, agent_id)
        if agent is None:
            return []

        workflow_ids = list(getattr(agent, "workflow_ids", []) or [])
        items: List[WorkflowDefinition] = []

        for workflow_id in workflow_ids:
            workflow = self.workflow_repository.get(workspace_id, workflow_id)
            if workflow is not None:
                items.append(workflow)

        return items

    def list_agent_triggers(
        self,
        workspace_id: str,
        agent_id: str,
    ) -> List[TriggerDefinition]:
        agent = self.get_agent(workspace_id, agent_id)
        if agent is None:
            return []

        trigger_ids = list(getattr(agent, "trigger_ids", []) or [])
        items: List[TriggerDefinition] = []

        for trigger_id in trigger_ids:
            trigger = self.trigger_repository.load_optional(workspace_id, trigger_id)
            if trigger is not None:
                items.append(trigger)

        return items

    def get_agent_bundle(
        self,
        workspace_id: str,
        agent_id: str,
    ) -> Dict[str, object] | None:
        agent = self.get_agent(workspace_id, agent_id)
        if agent is None:
            return None

        workflows = self.list_agent_workflows(workspace_id, agent_id)
        triggers = self.list_agent_triggers(workspace_id, agent_id)

        return {
            "agent": agent,
            "workflows": workflows,
            "triggers": triggers,
        }