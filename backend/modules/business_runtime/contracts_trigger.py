from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TriggerKind(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    KPI_THRESHOLD = "kpi_threshold"


@dataclass(slots=True)
class TriggerDefinition:
    id: str
    workflow_id: str
    kind: TriggerKind
    name: str
    is_enabled: bool = True
    schedule: Optional[str] = None
    condition: Dict[str, Any] = field(default_factory=dict)
    cooldown_seconds: int = 0
    dedupe_key: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)