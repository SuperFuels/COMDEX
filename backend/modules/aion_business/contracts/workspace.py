from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class GoalRef(BaseModel):
    id: str
    title: str
    status: str = "active"


class BusinessProfile(BaseModel):
    legal_name: Optional[str] = None
    trading_name: Optional[str] = None
    sector: Optional[str] = None
    stage: Optional[str] = None
    products: List[str] = Field(default_factory=list)
    customer_types: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)
    goals: List[GoalRef] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    preferred_style: List[str] = Field(default_factory=list)
    preferred_tools: List[str] = Field(default_factory=list)


class WorkspaceSpec(BaseModel):
    id: str
    name: str
    business_type: str
    owner: str

    deployment_mode: str = "local"
    provider_policy_ref: Optional[str] = None
    governance_policy_ref: Optional[str] = None

    business_profile: BusinessProfile = Field(default_factory=BusinessProfile)

    container_ids: List[str] = Field(default_factory=list)
    container_binding_ids: List[str] = Field(default_factory=list)   # <- add this
    role_ids: List[str] = Field(default_factory=list)
    tool_connections: List[str] = Field(default_factory=list)

    status: str = "active"