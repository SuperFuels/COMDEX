from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec


@dataclass
class EligibilityDecision:
    ok: bool
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
        }


class EligibilityChecker:
    """
    v1 governed spawn/run checks.

    Current checks:
    - workspace and role business type alignment
    - agent and role business type alignment
    - objective present
    - allowed skills present
    - allowed containers present
    - workspace exists / active
    - cost budget is non-negative

    Later extend with:
    - provider connectivity
    - approval gates
    - memory scope policy
    - tool connectivity
    - workflow ownership
    """

    def check_spawn(
        self,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        agent: AgentSpec,
        *,
        available_binding_ids: Optional[List[str]] = None,
        available_skill_ids: Optional[List[str]] = None,
    ) -> EligibilityDecision:
        reasons: List[str] = []
        warnings: List[str] = []

        binding_set = set(available_binding_ids or [])
        skill_set = set(available_skill_ids or [])

        if workspace.status != "active":
            reasons.append(f"workspace_not_active:{workspace.status}")

        if role.workspace_id != workspace.id:
            reasons.append("role_workspace_mismatch")

        if agent.business_type != workspace.business_type:
            reasons.append("agent_workspace_business_type_mismatch")

        if role.business_type != workspace.business_type:
            reasons.append("role_workspace_business_type_mismatch")

        if agent.role != role.role_type:
            reasons.append("agent_role_mismatch")

        if not agent.objective or not agent.objective.strip():
            reasons.append("missing_objective")

        if not agent.allowed_skills:
            reasons.append("missing_allowed_skills")

        if not agent.allowed_containers:
            warnings.append("no_allowed_containers")

        if agent.cost_budget < 0:
            reasons.append("negative_cost_budget")

        for skill_id in agent.allowed_skills:
            if skill_set and skill_id not in skill_set:
                reasons.append(f"unknown_skill:{skill_id}")

        for binding_id in agent.allowed_containers:
            if binding_set and binding_id not in binding_set:
                reasons.append(f"unknown_container_binding:{binding_id}")

        if role.allowed_skill_ids:
            for skill_id in agent.allowed_skills:
                if skill_id not in role.allowed_skill_ids:
                    reasons.append(f"skill_not_permitted_by_role:{skill_id}")

        if role.allowed_container_ids:
            for binding_id in agent.allowed_containers:
                if binding_id not in role.allowed_container_ids:
                    reasons.append(f"container_not_permitted_by_role:{binding_id}")

        if agent.trigger == "scheduled" and agent.agent_type == "task":
            warnings.append("scheduled_task_agent")

        return EligibilityDecision(
            ok=len(reasons) == 0,
            reasons=reasons,
            warnings=warnings,
        )