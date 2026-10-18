from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ModelRoute(str, Enum):
    DETERMINISTIC = "deterministic"
    LOCAL_LLM = "local_llm"
    CLOUD_LLM = "cloud_llm"
    HUMAN = "human"


class TaskType(str, Enum):
    SUMMARIZE = "summarize"
    CLASSIFY = "classify"
    EXTRACT = "extract"
    DRAFT_REPLY = "draft_reply"
    PLAN = "plan"
    JSON_MODE = "json_mode"
    GENERAL = "general"


@dataclass(slots=True)
class RoutingContext:
    workspace_id: Optional[str] = None
    seat_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RoutingRequest:
    task_type: TaskType
    prompt: str
    system: Optional[str] = None
    requires_json: bool = False
    prefers_local: bool = True
    allow_cloud_fallback: bool = False
    requires_human_approval: bool = False
    risk_level: str = "low"
    context: RoutingContext = field(default_factory=RoutingContext)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RoutingDecision:
    route: ModelRoute
    reason: str
    model: Optional[str] = None
    provider: Optional[str] = None
    fallback_route: Optional[ModelRoute] = None
    metadata: Dict[str, Any] = field(default_factory=dict)