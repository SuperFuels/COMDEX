from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from backend.modules.workflow_capsules.permissions.permission_modes import (
    PermissionMode,
    RiskTier,
)


@dataclass
class AgentPermissionProfile:
    agent_id: str = "agent.default"
    allowed_actions: List[str] = field(default_factory=list)
    blocked_actions: List[str] = field(default_factory=list)
    can_self_authorise_external_writes: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowPermissionPolicy:
    mode: PermissionMode = PermissionMode.REVIEW
    workflow_id: str = ""
    allowed_actions: List[str] = field(default_factory=list)
    requires_approval_for: List[str] = field(default_factory=list)
    blocked_actions: List[str] = field(default_factory=list)
    max_auto_sends_per_day: int = 0
    min_confidence: float = 0.86
    allowed_recipient_scope: str = "original_thread_only"
    allow_live_execute: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.value if isinstance(self.mode, PermissionMode) else self.mode
        return data


@dataclass
class PermissionEvaluationContext:
    workspace_id: str = ""
    agent_id: str = ""
    workflow_id: str = ""
    node_id: str = ""
    action: str = ""
    connector: Optional[str] = None
    risk_tier: RiskTier = RiskTier.LOW
    is_external_write: bool = False
    is_draft_action: bool = False
    requires_approval: bool = False
    confidence: Optional[float] = None
    risk_flags: List[str] = field(default_factory=list)
    execution_mode: str = "dry_run"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["risk_tier"] = (
            self.risk_tier.value if isinstance(self.risk_tier, RiskTier) else self.risk_tier
        )
        return data
