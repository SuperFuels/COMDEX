from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"


class TriggerState(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class TriggerDefinition(BaseModel):
    id: str
    workspace_id: str

    name: str
    description: Optional[str] = None

    trigger_type: TriggerType = TriggerType.MANUAL
    state: TriggerState = TriggerState.ACTIVE
    enabled: bool = True

    workflow_definition_id: str
    agent_definition_id: Optional[str] = None
    department_key: Optional[str] = None

    # first-pass schedule support: every X minutes only
    cadence_minutes: Optional[int] = Field(default=None, ge=1)

    # restart-safe schedule state
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    last_completed_at: Optional[str] = None
    last_attempted_at: Optional[str] = None

    cooldown_seconds: int = Field(default=0, ge=0)
    dedupe_key: Optional[str] = None
    last_dedupe_key: Optional[str] = None

    last_run_id: Optional[str] = None
    last_error: Optional[str] = None
    run_count: int = Field(default=0, ge=0)

    created_by: str = "system"
    updated_at: str = Field(default_factory=utc_now_iso)
    created_at: str = Field(default_factory=utc_now_iso)

    def is_schedulable(self) -> bool:
        return (
            self.trigger_type == TriggerType.SCHEDULE
            and self.enabled
            and self.state == TriggerState.ACTIVE
            and self.cadence_minutes is not None
            and self.cadence_minutes > 0
        )