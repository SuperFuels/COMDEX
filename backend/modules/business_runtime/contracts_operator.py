from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class OperatorState(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(slots=True)
class AgentOperator:
    id: str
    name: str
    department_key: str
    mission: str
    capability_ids: List[str] = field(default_factory=list)
    workflow_ids: List[str] = field(default_factory=list)
    state: OperatorState = OperatorState.DRAFT
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)