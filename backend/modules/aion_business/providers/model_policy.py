from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


RoutingLayer = Literal["none", "low_cost", "high_value", "specialist_runtime"]


class ModelPolicy(BaseModel):
    id: str

    default_provider: str
    fallback_provider: Optional[str] = None

    byok_required: bool = False
    max_cost_per_task: float = 0.0

    allowed_capabilities: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=list)

    escalation_threshold: Optional[str] = None
    no_model_for_skills: List[str] = Field(default_factory=list)

    preferred_routing_layer: RoutingLayer = "low_cost"
    metadata: Dict[str, str] = Field(default_factory=dict)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def allows_role(self, role_type: str) -> bool:
        if not self.allowed_roles:
            return True
        return role_type in self.allowed_roles

    def allows_capability(self, capability: str) -> bool:
        if not self.allowed_capabilities:
            return True
        return capability in self.allowed_capabilities

    def blocks_skill(self, skill_id: str) -> bool:
        return skill_id in self.no_model_for_skills

    def choose_provider(self, preferred_provider: Optional[str] = None) -> str:
        if preferred_provider and preferred_provider == self.default_provider:
            return self.default_provider
        if preferred_provider and self.fallback_provider and preferred_provider == self.fallback_provider:
            return self.fallback_provider
        return self.default_provider


def default_openai_copy_policy() -> ModelPolicy:
    return ModelPolicy(
        id="openai_for_copy",
        default_provider="openai",
        fallback_provider="anthropic",
        byok_required=False,
        max_cost_per_task=5.0,
        allowed_capabilities=[
            "drafting",
            "rewrite",
            "summarization",
            "reasoning",
        ],
        allowed_roles=["CEO", "CMO", "COO", "CTO", "RESEARCH", "FINANCE", "SUPPORT"],
        no_model_for_skills=[
            "read_container",
            "produce_report",
        ],
        preferred_routing_layer="high_value",
        metadata={"purpose": "polished_copy_and_business_reasoning"},
    )


def default_anthropic_reasoning_policy() -> ModelPolicy:
    return ModelPolicy(
        id="anthropic_reasoning",
        default_provider="anthropic",
        fallback_provider="openai",
        byok_required=False,
        max_cost_per_task=8.0,
        allowed_capabilities=[
            "reasoning",
            "analysis",
            "planning",
            "summarization",
        ],
        allowed_roles=["CEO", "CMO", "COO", "CTO", "RESEARCH"],
        no_model_for_skills=[
            "read_container",
        ],
        preferred_routing_layer="high_value",
        metadata={"purpose": "deep_reasoning_and_analysis"},
    )