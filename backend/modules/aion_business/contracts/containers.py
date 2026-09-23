from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


ContainerCategory = Literal[
    "policies",
    "products",
    "customers",
    "finance",
    "projects",
    "meetings",
    "marketing",
    "support",
    "research",
    "custom",
]

RuntimeBackend = Literal[
    "ucs",
    "container_runtime",
    "hoberman",
    "dc_json",
    "vault",
    "generated",
]

AccessPolicy = Literal[
    "role_scoped",
    "agent_scoped",
    "workflow_scoped",
    "admin_only",
]

SyncPolicy = Literal["manual", "scheduled", "live"]

ContainerStatus = Literal["active", "paused", "archived"]


class ContainerBindingSpec(BaseModel):
    """
    Aion Business binding over an existing AION/UCS container plus
    an optional KG semantic namespace/view.

    This is the business-facing container contract.
    """

    id: str = Field(..., min_length=1)
    workspace_id: str = Field(..., min_length=1)

    name: str = Field(..., min_length=1)
    category: ContainerCategory = "custom"

    runtime_backend: RuntimeBackend = "ucs"
    runtime_container_id: str = Field(..., min_length=1)

    kg_container_id: Optional[str] = None
    kg_topic_wa: Optional[str] = None
    kg_graph: str = "work"

    address: Optional[str] = None
    source_ref: Optional[str] = None
    geometry: Optional[str] = None

    access_policy: AccessPolicy = "role_scoped"
    sync_policy: SyncPolicy = "manual"

    writable: bool = False
    semantic_writes_enabled: bool = True

    role_allowlist: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    description: Optional[str] = None
    status: ContainerStatus = "active"