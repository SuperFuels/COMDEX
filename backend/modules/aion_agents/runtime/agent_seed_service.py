from __future__ import annotations

from typing import Dict

from backend.modules.aion_agents.runtime.agent_definition_repository import (
    AgentDefinitionRepository,
)
from backend.modules.aion_agents.runtime.marketing_operator_seed import (
    build_marketing_seed_bundle,
)
from backend.modules.aion_agents.runtime.trigger_definition_repository import (
    TriggerDefinitionRepository,
)
from backend.modules.aion_agents.runtime.workflow_definition_repository import (
    WorkflowDefinitionRepository,
)


class AgentSeedService:
    def __init__(
        self,
        *,
        workflow_repository: WorkflowDefinitionRepository,
        agent_repository: AgentDefinitionRepository,
        trigger_repository: TriggerDefinitionRepository,
    ) -> None:
        self.workflow_repository = workflow_repository
        self.agent_repository = agent_repository
        self.trigger_repository = trigger_repository

    def ensure_marketing_operator_seed(self, workspace_id: str) -> Dict[str, object]:
        bundle = build_marketing_seed_bundle(workspace_id)

        workflow = bundle["workflow"]
        agent = bundle["agent"]
        trigger = bundle["trigger"]

        self.workflow_repository.save(workflow)
        self.agent_repository.save(agent)
        self.trigger_repository.save(trigger)

        return {
            "ok": True,
            "workspace_id": workspace_id,
            "workflow_id": getattr(workflow, "workflow_id", getattr(workflow, "id", None)),
            "agent_id": getattr(agent, "agent_id", getattr(agent, "id", None)),
            "trigger_id": getattr(trigger, "trigger_id", getattr(trigger, "id", None)),
        }