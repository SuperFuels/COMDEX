from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


TopologyNodeType = Literal[
    "workspace",
    "department",
    "function",
    "channel",
    "service",
    "revenue_stream",
    "cost_item",
    "payment_terms",
    "fulfillment_process",
    "team",
    "human_agent",
    "ai_agent",
]

TopologyEdgeType = Literal[
    "owns",
    "contains",
    "operates",
    "delivers",
    "sells_through",
    "earns_from",
    "costs_for",
    "paid_by",
    "fulfilled_by",
    "staffed_by",
    "supported_by",
    "reports_to",
    "uses",
]


class TopologyNode(BaseModel):
    id: str
    workspace_id: str

    node_type: TopologyNodeType
    ref_id: str

    label: str
    description: Optional[str] = None

    metadata: Dict[str, str] = Field(default_factory=dict)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class TopologyEdge(BaseModel):
    id: str
    workspace_id: str

    edge_type: TopologyEdgeType
    from_node_id: str
    to_node_id: str

    label: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class BusinessTopology(BaseModel):
    workspace_id: str
    nodes: List[TopologyNode] = Field(default_factory=list)
    edges: List[TopologyEdge] = Field(default_factory=list)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)