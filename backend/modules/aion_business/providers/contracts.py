from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


ProviderCapability = Literal[
    "drafting",
    "rewrite",
    "summarization",
    "analysis",
    "reasoning",
    "planning",
    "classification",
]


class ProviderRequest(BaseModel):
    provider: str
    model: Optional[str] = None

    prompt: str
    system_prompt: Optional[str] = None

    capability: ProviderCapability = "drafting"
    role_type: Optional[str] = None
    skill_id: Optional[str] = None

    policy_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    max_tokens: int = 512
    temperature: Optional[float] = None
    created_at: str = Field(default_factory=utc_now_iso)


class ProviderResult(BaseModel):
    ok: bool

    provider: str
    model: str
    content: str

    usage: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0

    fallback_used: bool = False
    error_code: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    policy_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    completed_at: str = Field(default_factory=utc_now_iso)