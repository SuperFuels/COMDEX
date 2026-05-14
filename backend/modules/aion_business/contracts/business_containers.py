from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


BusinessContainerKind = Literal[
    "business_identity",
    "business_structure",
    "brand_foundation",
    "boardroom_snapshot",
    "operational_runtime_summary",
]


class BusinessContainerMeta(BaseModel):
    workspace_id: str
    container_key: BusinessContainerKind
    version: str = "v1"
    updated_at: Optional[str] = None
    source: str = "local_runtime"


class BusinessIdentityContainer(BaseModel):
    id: str
    workspace_id: str
    kind: Literal["business_identity"] = "business_identity"
    meta: BusinessContainerMeta

    legal_name: Optional[str] = None
    trading_name: Optional[str] = None
    business_type: Optional[str] = None
    sector: Optional[str] = None
    stage: Optional[str] = None
    owner: Optional[str] = None

    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None

    primary_domain: Optional[str] = None
    website_url: Optional[str] = None
    primary_email: Optional[str] = None
    description: Optional[str] = None

    source_refs: List[str] = Field(default_factory=list)


class BusinessStructureContainer(BaseModel):
    id: str
    workspace_id: str
    kind: Literal["business_structure"] = "business_structure"
    meta: BusinessContainerMeta

    identity: Dict[str, Any] = Field(default_factory=dict)
    channels: List[Dict[str, Any]] = Field(default_factory=list)
    services: List[Dict[str, Any]] = Field(default_factory=list)
    revenue_streams: List[Dict[str, Any]] = Field(default_factory=list)
    cost_items: List[Dict[str, Any]] = Field(default_factory=list)
    payment_terms: List[Dict[str, Any]] = Field(default_factory=list)
    fulfillment_processes: List[Dict[str, Any]] = Field(default_factory=list)
    functions: List[Dict[str, Any]] = Field(default_factory=list)
    teams: List[Dict[str, Any]] = Field(default_factory=list)
    human_agents: List[Dict[str, Any]] = Field(default_factory=list)
    ai_agents: List[Dict[str, Any]] = Field(default_factory=list)


class BrandFoundationContainer(BaseModel):
    id: str
    workspace_id: str
    kind: Literal["brand_foundation"] = "brand_foundation"
    meta: BusinessContainerMeta

    objective: Optional[str] = None
    funnel_goal: Optional[str] = None
    target_audience: Optional[str] = None
    persona: Optional[str] = None
    offer: Optional[str] = None

    channels: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    hard_rules: List[str] = Field(default_factory=list)
    guidance_notes: List[str] = Field(default_factory=list)
    campaign_notes: List[str] = Field(default_factory=list)

    brand_intelligence_map: Dict[str, Any] = Field(default_factory=dict)
    brand_map: Dict[str, Any] = Field(default_factory=dict)

    brand_overview: Dict[str, Any] = Field(default_factory=dict)
    brand_goals: Dict[str, Any] = Field(default_factory=dict)
    brand_purpose: Dict[str, Any] = Field(default_factory=dict)
    brand_vision: Dict[str, Any] = Field(default_factory=dict)
    brand_mission: Dict[str, Any] = Field(default_factory=dict)
    brand_values: Dict[str, Any] = Field(default_factory=dict)
    brand_positioning: Dict[str, Any] = Field(default_factory=dict)
    brand_personality: Dict[str, Any] = Field(default_factory=dict)
    brand_voice: Dict[str, Any] = Field(default_factory=dict)
    brand_story: Dict[str, Any] = Field(default_factory=dict)
    tagline: Optional[str] = None

    audience: Dict[str, Any] = Field(default_factory=dict)
    audience_segments: List[Dict[str, Any]] = Field(default_factory=list)
    customer_personas: List[Dict[str, Any]] = Field(default_factory=list)
    customer_journey: List[Dict[str, Any]] = Field(default_factory=list)
    customer_pain_points: List[str] = Field(default_factory=list)

    competitor_analysis: Dict[str, Any] = Field(default_factory=dict)
    competitor_urls: List[str] = Field(default_factory=list)
    differentiation: Dict[str, Any] = Field(default_factory=dict)

    platform_strategy: Dict[str, Any] = Field(default_factory=dict)
    messaging_rules: Dict[str, Any] = Field(default_factory=dict)
    visual_identity: Dict[str, Any] = Field(default_factory=dict)
    governance: Dict[str, Any] = Field(default_factory=dict)


class BoardroomSnapshotContainer(BaseModel):
    id: str
    workspace_id: str
    kind: Literal["boardroom_snapshot"] = "boardroom_snapshot"
    meta: BusinessContainerMeta

    topology: Dict[str, Any] = Field(default_factory=dict)
    boardroom: Dict[str, Any] = Field(default_factory=dict)


class OperationalRuntimeSummaryContainer(BaseModel):
    id: str
    workspace_id: str
    kind: Literal["operational_runtime_summary"] = "operational_runtime_summary"
    meta: BusinessContainerMeta

    dashboard_summary: Dict[str, Any] = Field(default_factory=dict)
    marketing_summary: Dict[str, Any] = Field(default_factory=dict)
    runtime_summary: Dict[str, Any] = Field(default_factory=dict)


BusinessContainerModel = (
    BusinessIdentityContainer
    | BusinessStructureContainer
    | BrandFoundationContainer
    | BoardroomSnapshotContainer
    | OperationalRuntimeSummaryContainer
)