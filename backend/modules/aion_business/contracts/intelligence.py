from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, model_validator

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


AdapterKind = Literal["capability", "model", "retrieval", "evidence", "agent_harness"]
AdapterLocation = Literal["local", "customer_cloud", "external_api"]
DeliveryMode = Literal["pilot_presentation", "governed_capability"]


class IntelligenceBudget(BaseModel):
    minimum_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    maximum_cost: float = Field(default=0.0, ge=0.0)
    maximum_latency_ms: int = Field(default=30_000, ge=1)
    maximum_energy_wh: float = Field(default=1.0, ge=0.0)
    maximum_context_bytes: int = Field(default=128_000, ge=1)
    maximum_attempts: int = Field(default=3, ge=1, le=8)


class DisclosurePolicy(BaseModel):
    data_classification: Literal["public", "internal", "confidential", "restricted"] = "internal"
    allow_external: bool = False
    allowed_destinations: List[str] = Field(default_factory=list)
    allowed_residencies: List[str] = Field(default_factory=list)
    declared_fields: List[str] = Field(default_factory=list)


class DeliveryTarget(BaseModel):
    mode: DeliveryMode = "pilot_presentation"
    surface: str = "pilot"
    capability_id: str = ""
    approval_receipt: str = ""

    @model_validator(mode="after")
    def validate_capability(self):
        if self.mode == "governed_capability" and not self.capability_id.strip():
            raise ValueError("capability_id_required")
        return self


class IntelligenceRequest(BaseModel):
    schema_version: str = "aion.intelligence.request.v1"
    request_id: str
    brain_id: str
    task_class: str
    input: Dict[str, Any]
    required_capabilities: List[str] = Field(default_factory=list)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    budget: IntelligenceBudget = Field(default_factory=IntelligenceBudget)
    disclosure: DisclosurePolicy = Field(default_factory=DisclosurePolicy)
    delivery: DeliveryTarget = Field(default_factory=DeliveryTarget)
    created_at: str = Field(default_factory=utc_now_iso)

    @model_validator(mode="after")
    def validate_identity(self):
        if not self.request_id.strip():
            raise ValueError("request_id_required")
        if not self.brain_id.strip():
            raise ValueError("brain_id_required")
        if not self.task_class.strip():
            raise ValueError("task_class_required")
        return self

    def content_hash(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class IntelligenceAdapterManifest(BaseModel):
    schema_version: str = "aion.intelligence.adapter.v1"
    adapter_id: str
    kind: AdapterKind
    location: AdapterLocation
    provider: str = "aion"
    model: str = ""
    capabilities: List[str] = Field(default_factory=list)
    destination: str = "local"
    residency: str = "local"
    maximum_data_classification: Literal["public", "internal", "confidential", "restricted"] = "restricted"
    estimated_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    estimated_cost: float = Field(default=0.0, ge=0.0)
    estimated_latency_ms: int = Field(default=0, ge=0)
    estimated_energy_wh: float = Field(default=0.0, ge=0.0)


class IntelligenceAttempt(BaseModel):
    adapter_id: str
    kind: AdapterKind
    status: Literal["succeeded", "failed", "skipped"]
    reason: str = ""
    latency_ms: int = 0
    cost: float = 0.0
    energy_wh: float = 0.0
    quality_score: float = 0.0
    external: bool = False


class IntelligenceResponse(BaseModel):
    schema_version: str = "aion.intelligence.response.v1"
    request_id: str
    ok: bool
    status: Literal["completed", "limited", "failed"]
    output: Dict[str, Any] = Field(default_factory=dict)
    adapter_id: str = ""
    attempts: List[IntelligenceAttempt] = Field(default_factory=list)
    delivery: Dict[str, Any] = Field(default_factory=dict)
    receipt: Dict[str, Any] = Field(default_factory=dict)
    completed_at: str = Field(default_factory=utc_now_iso)


class IntelligenceStreamEvent(BaseModel):
    schema_version: str = "aion.intelligence.stream.v1"
    request_id: str
    sequence: int = Field(ge=0)
    event: Literal["accepted", "route_attempt", "fallback", "delivery", "completed", "failed"]
    payload: Dict[str, Any] = Field(default_factory=dict)
    emitted_at: str = Field(default_factory=utc_now_iso)


def published_intelligence_schemas() -> Dict[str, Dict[str, Any]]:
    """Portable JSON schemas for app, server and customer-cloud implementations."""
    return {
        "request": IntelligenceRequest.model_json_schema(),
        "response": IntelligenceResponse.model_json_schema(),
        "stream_event": IntelligenceStreamEvent.model_json_schema(),
        "adapter_manifest": IntelligenceAdapterManifest.model_json_schema(),
    }
