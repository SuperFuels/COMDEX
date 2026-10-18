from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.contracts.ai_agents import AIAgentSpec
from backend.modules.aion_business.contracts.business_identity import BusinessIdentity
from backend.modules.aion_business.contracts.channels import BusinessChannel
from backend.modules.aion_business.contracts.cost_structure import CostLineItem
from backend.modules.aion_business.contracts.fulfillment import FulfillmentProcess
from backend.modules.aion_business.contracts.functions import BusinessFunctionSpec
from backend.modules.aion_business.contracts.human_agents import HumanAgentSpec
from backend.modules.aion_business.contracts.payment_terms import PaymentTerms
from backend.modules.aion_business.contracts.revenue_streams import RevenueStream
from backend.modules.aion_business.contracts.services import ServiceOffer
from backend.modules.aion_business.contracts.teams import TeamSpec
from backend.modules.aion_business.contracts.topology import BusinessTopology
from backend.modules.aion_business.runtime.business_container_service import (
    BusinessContainerService,
)
from backend.modules.aion_business.runtime.service_business_topology_generator import (
    ServiceBusinessTopologyGenerator,
)
from backend.modules.aion_business.runtime.topology_repository import TopologyRepository

router = APIRouter(
    prefix="/api/aion/business/topology",
    tags=["aion-business-topology"],
)


def get_generator() -> ServiceBusinessTopologyGenerator:
    return ServiceBusinessTopologyGenerator()


def get_repository() -> TopologyRepository:
    return TopologyRepository()


def get_business_container_service() -> BusinessContainerService:
    return BusinessContainerService()


class GenerateTopologyRequest(BaseModel):
    identity: BusinessIdentity

    channels: List[BusinessChannel] = Field(default_factory=list)
    services: List[ServiceOffer] = Field(default_factory=list)
    revenue_streams: List[RevenueStream] = Field(default_factory=list)
    cost_items: List[CostLineItem] = Field(default_factory=list)
    payment_terms: List[PaymentTerms] = Field(default_factory=list)
    fulfillment_processes: List[FulfillmentProcess] = Field(default_factory=list)
    functions: List[BusinessFunctionSpec] = Field(default_factory=list)
    teams: List[TeamSpec] = Field(default_factory=list)
    human_agents: List[HumanAgentSpec] = Field(default_factory=list)
    ai_agents: List[AIAgentSpec] = Field(default_factory=list)

    persist: bool = True


class GenerateTopologyResponse(BaseModel):
    topology: BusinessTopology
    persisted: bool = False
    source: str = "request"


class TopologyExistsResponse(BaseModel):
    workspace_id: str
    exists: bool
    source: Optional[str] = None


def _generate_from_request(request: GenerateTopologyRequest) -> BusinessTopology:
    generator = get_generator()

    return generator.generate(
        identity=request.identity,
        channels=request.channels,
        services=request.services,
        revenue_streams=request.revenue_streams,
        cost_items=request.cost_items,
        payment_terms=request.payment_terms,
        fulfillment_processes=request.fulfillment_processes,
        functions=request.functions,
        teams=request.teams,
        human_agents=request.human_agents,
        ai_agents=request.ai_agents,
    )


def _load_canonical_topology(workspace_id: str) -> Optional[BusinessTopology]:
    service = get_business_container_service()

    try:
        service.ensure_canonical_containers(workspace_id)
        payload = service.get_topology_payload(workspace_id)
        if isinstance(payload, dict) and payload:
            return BusinessTopology(**payload)
    except Exception:
        return None

    return None


@router.post("/generate", response_model=GenerateTopologyResponse)
def generate_topology(request: GenerateTopologyRequest) -> GenerateTopologyResponse:
    """
    Explicit import/generate path.

    Raw request-driven topology generation is allowed here, but any persisted
    topology must be written back through the canonical container-backed sync path
    so topology and boardroom projections remain aligned.
    """
    repository = get_repository()
    service = get_business_container_service()

    try:
        topology = _generate_from_request(request)

        persisted = False
        if request.persist:
            sync_fn = getattr(service, "sync_topology_projection", None)
            if callable(sync_fn):
                sync_fn(
                    workspace_id=request.identity.workspace_id,
                    topology=topology.model_dump(mode="json"),
                )
            else:
                # Emergency legacy fallback only if canonical sync is unavailable.
                repository.save(topology)
            persisted = True

        return GenerateTopologyResponse(
            topology=topology,
            persisted=persisted,
            source="request",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.get("/{workspace_id}", response_model=BusinessTopology)
def get_topology(workspace_id: str) -> BusinessTopology:
    topology = _load_canonical_topology(workspace_id)
    if topology is not None:
        return topology

    raise HTTPException(
        status_code=404,
        detail=f"Canonical topology not found for workspace: {workspace_id}",
    )


@router.delete("/{workspace_id}")
def delete_topology(workspace_id: str) -> dict:
    """
    Deletes only the legacy persisted topology projection file.

    Canonical topology is container-derived and is not removed here.
    """
    repository = get_repository()
    deleted = repository.delete(workspace_id)
    return {
        "workspace_id": workspace_id,
        "deleted": deleted,
        "detail": (
            "Legacy topology projection file deleted only. "
            "Canonical topology is container-derived and was not removed."
        ),
    }


@router.get("/{workspace_id}/exists", response_model=TopologyExistsResponse)
def topology_exists(workspace_id: str) -> TopologyExistsResponse:
    topology = _load_canonical_topology(workspace_id)
    return TopologyExistsResponse(
        workspace_id=workspace_id,
        exists=topology is not None,
        source="containers" if topology is not None else "none",
    )