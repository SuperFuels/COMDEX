from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


BusinessContainerKind = Literal[
    "business_identity",
    "business_structure",
    "business_map",
    "department_intelligence",
    "business_financial_model",
    "business_operating_model",
    "organization_authority",
    "finance_inbox",
    "brand_foundation",
    "boardroom_snapshot",
    "operational_runtime_summary",
    "goal_engine_outcomes",
    "goal_engine_loops",
    "goal_engine_experiments",
    "goal_engine_evidence",
    "goal_engine_memory",
    "goal_engine_state",
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


class BusinessMapContainer(BaseModel):
    id: str
    workspace_id: str
    kind: Literal["business_map"] = "business_map"
    meta: BusinessContainerMeta

    facts: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    unknowns: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    unanswered_fields: List[str] = Field(default_factory=list)
    department_discovery_gaps: List[str] = Field(default_factory=list)
    source_refs: List[str] = Field(default_factory=list)
    revision: int = 1


class DepartmentIntelligenceContainer(BaseModel):
    id: str
    workspace_id: str
    kind: Literal["department_intelligence"] = "department_intelligence"
    meta: BusinessContainerMeta

    departments: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    revision: int = 1


class BusinessFinancialModelContainer(BaseModel):
    id: str
    workspace_id: str
    kind: Literal["business_financial_model"] = "business_financial_model"
    meta: BusinessContainerMeta

    model_status: str = "draft"
    currency: Optional[str] = None
    period_basis: str = "annual"
    reporting_period: Dict[str, Any] = Field(default_factory=dict)
    discovery_state: Dict[str, Any] = Field(default_factory=dict)
    revenue_model: Dict[str, Any] = Field(default_factory=dict)
    pricing_model: Dict[str, Any] = Field(default_factory=dict)
    direct_cost_model: Dict[str, Any] = Field(default_factory=dict)
    overhead_model: Dict[str, Any] = Field(default_factory=dict)
    cashflow_model: Dict[str, Any] = Field(default_factory=dict)
    capacity_model: Dict[str, Any] = Field(default_factory=dict)
    tax_context: Dict[str, Any] = Field(default_factory=dict)
    integration_evidence: Dict[str, Any] = Field(default_factory=dict)
    external_data: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    authoritative_metrics: Dict[str, Any] = Field(default_factory=dict)
    financial_statements: Dict[str, Any] = Field(default_factory=dict)
    business_model: Dict[str, Any] = Field(default_factory=dict)
    statement_quality: Dict[str, Any] = Field(default_factory=dict)
    finance_director: Dict[str, Any] = Field(default_factory=dict)
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    completion_receipt: Dict[str, Any] = Field(default_factory=dict)
    revision: int = 1


class BusinessOperatingModelContainer(BaseModel):
    """Canonical cross-functional description of what the business sells and delivers.

    This container deliberately sits beside (not inside) Finance. Products & Services
    owns the catalogue, Operations owns recipes/capacity/stock, HR owns labour inputs,
    Sales owns customer terms and Finance consumes the calculated economics.
    """

    id: str
    workspace_id: str
    kind: Literal["business_operating_model"] = "business_operating_model"
    meta: BusinessContainerMeta

    model_status: str = "draft"
    setup_mode: str = "simple"
    currency: str = "EUR"
    offerings: List[Dict[str, Any]] = Field(default_factory=list)
    pricing_rules: List[Dict[str, Any]] = Field(default_factory=list)
    payment_terms: List[Dict[str, Any]] = Field(default_factory=list)
    customer_terms: List[Dict[str, Any]] = Field(default_factory=list)
    labour_resources: List[Dict[str, Any]] = Field(default_factory=list)
    jobs: List[Dict[str, Any]] = Field(default_factory=list)
    job_labour_assignments: List[Dict[str, Any]] = Field(default_factory=list)
    job_cost_items: List[Dict[str, Any]] = Field(default_factory=list)
    job_economics: List[Dict[str, Any]] = Field(default_factory=list)
    overheads: List[Dict[str, Any]] = Field(default_factory=list)
    debt_commitments: List[Dict[str, Any]] = Field(default_factory=list)
    financial_targets: List[Dict[str, Any]] = Field(default_factory=list)
    production_lines: List[Dict[str, Any]] = Field(default_factory=list)
    bills_of_materials: List[Dict[str, Any]] = Field(default_factory=list)
    inventory_items: List[Dict[str, Any]] = Field(default_factory=list)
    suppliers: List[Dict[str, Any]] = Field(default_factory=list)
    procurement_queue: List[Dict[str, Any]] = Field(default_factory=list)
    unit_economics: List[Dict[str, Any]] = Field(default_factory=list)
    inventory_metrics: Dict[str, Any] = Field(default_factory=dict)
    capacity_model: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    source_refs: List[Dict[str, Any]] = Field(default_factory=list)
    revision: int = 1


class OrganizationAuthorityContainer(BaseModel):
    """Minimal people, organisation and application-authority source of truth."""

    id: str
    workspace_id: str
    kind: Literal["organization_authority"] = "organization_authority"
    meta: BusinessContainerMeta

    model_status: str = "setup_required"
    people: List[Dict[str, Any]] = Field(default_factory=list)
    departments: List[Dict[str, Any]] = Field(default_factory=list)
    roles: List[Dict[str, Any]] = Field(default_factory=list)
    authority_policies: List[Dict[str, Any]] = Field(default_factory=list)
    assets: List[Dict[str, Any]] = Field(default_factory=list)
    people_operations: Dict[str, Any] = Field(default_factory=dict)
    external_sources: List[Dict[str, Any]] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    revision: int = 1


class FinanceInboxContainer(BaseModel):
    """Provider-neutral intake and approval ledger for transaction documents."""

    id: str
    workspace_id: str
    kind: Literal["finance_inbox"] = "finance_inbox"
    meta: BusinessContainerMeta

    model_status: str = "empty"
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    intake_channels: List[Dict[str, Any]] = Field(default_factory=list)
    accounting_destinations: List[Dict[str, Any]] = Field(default_factory=list)
    expense_policy: Dict[str, Any] = Field(default_factory=dict)
    learned_mappings: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    governance: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    revision: int = 1


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
    | BusinessMapContainer
    | DepartmentIntelligenceContainer
    | BusinessFinancialModelContainer
    | BusinessOperatingModelContainer
    | OrganizationAuthorityContainer
    | FinanceInboxContainer
    | BrandFoundationContainer
    | BoardroomSnapshotContainer
    | OperationalRuntimeSummaryContainer
)
