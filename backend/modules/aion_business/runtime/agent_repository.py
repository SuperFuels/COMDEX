from __future__ import annotations

import json
from typing import List

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.department_operational_store import BusinessOperationsRecordRepository, DepartmentOperationalStore


class AgentRepository:
    def __init__(self, *, operational_store: DepartmentOperationalStore | None = None) -> None:
        self.records = BusinessOperationsRecordRepository("agents", operational_store=operational_store)

    def _agent_path(self, workspace_id: str, agent_id: str):
        return AIONBusinessPaths.agent_file(workspace_id, agent_id)

    def save(self, agent: AgentSpec):
        if self.records.enabled:
            self.records.put(agent.workspace_id, agent.id, agent.model_dump(mode="json"), actor_id="agent-repository")
            return f"vault://departments.operational.records/{agent.workspace_id}/business_operations/agents/{agent.id}"
        path = self._agent_path(agent.workspace_id, agent.id)
        path.write_text(
            json.dumps(agent.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, workspace_id: str, agent_id: str) -> AgentSpec:
        if self.records.enabled:
            record = self.records.get_optional(workspace_id, agent_id)
            if record is None:
                raise FileNotFoundError(f"Agent not found: {workspace_id}/{agent_id}")
            return AgentSpec(**record["payload"])
        path = self._agent_path(workspace_id, agent_id)
        if not path.exists():
            raise FileNotFoundError(f"Agent not found: {workspace_id}/{agent_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return AgentSpec(**data)

    def list_ids(self, workspace_id: str) -> List[str]:
        if self.records.enabled:
            return sorted(str(row["payload"]["id"]) for row in self.records.list_workspace(workspace_id))
        path = AIONBusinessPaths.agent_dir(workspace_id)
        return sorted(p.stem for p in path.glob("*.json"))

    def list_all(self, workspace_id: str) -> List[AgentSpec]:
        return [self.load(workspace_id, agent_id) for agent_id in self.list_ids(workspace_id)]
