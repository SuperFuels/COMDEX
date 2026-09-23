from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


SkillCategory = Literal["read", "transform", "write", "external_delegate", "analysis", "communication"]
SideEffectLevel = Literal["none", "low", "medium", "high"]


class SkillSpec(BaseModel):
    id: str
    name: str
    category: SkillCategory
    version: str = "v1"
    input_schema_ref: Optional[str] = None
    output_schema_ref: Optional[str] = None
    side_effect_level: SideEffectLevel = "none"
    required_permissions: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=list)
    allowed_agent_types: List[str] = Field(default_factory=list)
    retry_policy_ref: Optional[str] = None
    audit_required: bool = True


class SkillRunRequest(BaseModel):
    skill_id: str
    agent_id: str
    task_id: Optional[str] = None
    objective: str
    input_payload: dict = Field(default_factory=dict)
    allowed_tools: List[str] = Field(default_factory=list)
    allowed_containers: List[str] = Field(default_factory=list)
    trace_required: bool = True


class SkillRunResult(BaseModel):
    ok: bool
    skill_id: str
    output_payload: dict = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    error_code: Optional[str] = None
    trace: dict = Field(default_factory=dict)
    side_effects_applied: bool = False