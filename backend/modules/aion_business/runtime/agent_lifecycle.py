from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from backend.modules.aion_business.contracts.agents import AgentSpec, AgentLifecycleState
from backend.modules.aion_business.runtime.agent_repository import AgentRepository


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


_ALLOWED_TRANSITIONS: dict[AgentLifecycleState, set[AgentLifecycleState]] = {
    "defined": {"eligible", "terminated"},
    "eligible": {"spawned", "terminated"},
    "spawned": {"initialized", "terminated"},
    "initialized": {"running", "blocked", "failed", "terminated"},
    "running": {"blocked", "completed", "failed", "escalated", "terminated"},
    "blocked": {"running", "escalated", "failed", "terminated"},
    "completed": {"terminated"},
    "failed": {"escalated", "terminated"},
    "escalated": {"running", "terminated"},
    "terminated": set(),
}


class AgentLifecycleError(ValueError):
    pass


class AgentLifecycle:
    def __init__(self, repository: AgentRepository | None = None):
        self.repository = repository or AgentRepository()

    @staticmethod
    def utc_now_iso() -> str:
        return utc_now_iso()

    def can_transition(
        self,
        current: AgentLifecycleState,
        target: AgentLifecycleState,
    ) -> bool:
        return target in _ALLOWED_TRANSITIONS.get(current, set())

    def transition_agent(
        self,
        agent: AgentSpec,
        target_state: AgentLifecycleState,
        *,
        persist: bool = False,
    ) -> AgentSpec:
        current = agent.lifecycle_state

        if not self.can_transition(current, target_state):
            raise AgentLifecycleError(
                f"Invalid lifecycle transition for agent {agent.id}: "
                f"{current} -> {target_state}"
            )

        agent.lifecycle_state = target_state
        agent.updated_at = utc_now_iso()

        if persist:
            self.repository.save(agent)

        return agent

    def transition(
        self,
        workspace_id: str,
        agent_id: str,
        target_state: AgentLifecycleState,
    ) -> AgentSpec:
        agent = self.repository.load(workspace_id, agent_id)
        return self.transition_agent(agent, target_state, persist=True)

    def bulk_transition(
        self,
        workspace_id: str,
        agent_ids: Iterable[str],
        target_state: AgentLifecycleState,
    ) -> list[AgentSpec]:
        out: list[AgentSpec] = []
        for agent_id in agent_ids:
            out.append(self.transition(workspace_id, agent_id, target_state))
        return out