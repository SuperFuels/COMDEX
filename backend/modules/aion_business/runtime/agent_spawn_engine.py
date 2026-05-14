from __future__ import annotations

from typing import Optional
from uuid import uuid4

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.agent_repository import AgentRepository
from backend.modules.aion_business.runtime.eligibility import EligibilityChecker, EligibilityDecision


class AgentSpawnEngine:
    def __init__(
        self,
        repository: Optional[AgentRepository] = None,
        eligibility_checker: Optional[EligibilityChecker] = None,
    ):
        self.repository = repository or AgentRepository()
        self.eligibility_checker = eligibility_checker or EligibilityChecker()

    def build_task_agent_spec(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        task: TaskRecord,
        output_contract: str = "task_output_v1",
        ttl_seconds: int = 3600,
        writable: bool = False,
    ) -> AgentSpec:
        role_type = str(role.role_type)
        short_id = uuid4().hex[:12]

        return AgentSpec(
            id=f"agent-{short_id}",
            workspace_id=workspace.id,
            agent_type="task",
            role=role_type,
            parent_role_id=role.id,
            business_type=workspace.business_type,
            objective=task.objective,
            allowed_skills=list(role.allowed_skill_ids),
            allowed_tools=[],
            allowed_containers=list(task.linked_containers or role.allowed_container_ids),
            memory_scope="task",
            output_contract=output_contract,
            trigger="delegated",
            escalation_rules=["role_review_required"],
            cost_budget=0.0,
            model_policy_ref=role.model_policy_ref,
            ttl_seconds=ttl_seconds,
            writable=writable,
            lifecycle_state="defined",
        )

    def check_task_agent_eligibility(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        agent_spec: AgentSpec,
    ) -> EligibilityDecision:
        return self.eligibility_checker.check_spawn(
            workspace,
            role,
            agent_spec,
            available_binding_ids=list(workspace.container_binding_ids),
            available_skill_ids=list(role.allowed_skill_ids),
        )

    def spawn_task_agent(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        task: TaskRecord,
        output_contract: str = "task_output_v1",
        ttl_seconds: int = 3600,
        writable: bool = False,
    ) -> AgentSpec:
        agent_spec = self.build_task_agent_spec(
            workspace=workspace,
            role=role,
            task=task,
            output_contract=output_contract,
            ttl_seconds=ttl_seconds,
            writable=writable,
        )

        decision = self.check_task_agent_eligibility(
            workspace=workspace,
            role=role,
            agent_spec=agent_spec,
        )

        if not decision.ok:
            joined = ", ".join(decision.reasons) or "unknown_eligibility_failure"
            raise ValueError(f"Agent spawn rejected: {joined}")

        agent_spec.lifecycle_state = "spawned"
        self.repository.save(agent_spec)
        return agent_spec