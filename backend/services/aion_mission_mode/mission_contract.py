"""
AION Phase 20A Mission Contract v0

Contract:
- Backend-only.
- Deterministic mission permission envelope.
- No live tools.
- No external writes.
- No reputation mutation.
- No chain write.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from hashlib import sha256
import json
from typing import Any, Literal
from enum import Enum


AutonomyLane = Literal[
    "research",
    "creation",
    "internal_ops",
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
]

MissionStatus = Literal[
    "created",
    "planning",
    "waiting_mission_approval",
    "running_autonomous_steps",
    "paused_at_checkpoint",
    "waiting_human_review",
    "blocked",
    "completed",
    "failed",
    "expired",
    "cancelled",
]


DEFAULT_HARD_BLOCKED_LANES: tuple[AutonomyLane, ...] = (
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
)



class MissionMode(str, Enum):
    """AION Pilot / Mission Mode execution mode."""

    OBSERVE_ONLY = "observe_only"
    PREVIEW_ONLY = "preview_only"
    CHECKPOINTED_AUTONOMY = "checkpointed_autonomy"
    APPROVED_EXECUTION = "approved_execution"


@dataclass(frozen=True)
class MissionCheckpoint:
    checkpoint_id: str
    title: str
    description: str
    required_before_step_id: str
    lane: AutonomyLane
    action_type: str
    required_action_type: str = ""
    risk_level: str = "medium"
    payload_hash: str | None = None
    expires_at: str | None = None


@dataclass(frozen=True)
class AionMissionContract:
    mission_id: str
    mission_goal: str
    business_id: str
    creator_id: str

    agent_mode: str = "checkpointed_autonomy"
    allowed_autonomy_lanes: tuple[AutonomyLane, ...] = ("research", "creation", "internal_ops")
    hard_blocked_lanes: tuple[AutonomyLane, ...] = DEFAULT_HARD_BLOCKED_LANES

    human_checkpoints: tuple[MissionCheckpoint, ...] = field(default_factory=tuple)
    approval_required_actions: tuple[str, ...] = (
        "send_email",
        "send_whatsapp",
        "post_social",
        "create_booking",
        "take_payment",
        "create_escrow",
        "deploy_live",
        "dispatch_worker",
        "mutate_business_memory",
    )

    max_runtime_seconds: int = 1800
    max_tool_calls: int = 50
    max_cost: float = 0.0

    proof_required: bool = True
    replay_required: bool = True
    ets_enabled: bool = True

    data_retention_policy: str = "mission_scoped"
    external_communication_consent_required: bool = True
    proof_sharing_enabled: bool = False

    status: MissionStatus = "created"

    live_external_writes_enabled: bool = False
    live_payment_enabled: bool = False
    live_booking_enabled: bool = False
    live_deployment_enabled: bool = False
    live_reputation_mutation_enabled: bool = False
    live_chain_write_enabled: bool = False

    schema_version: str = "aion.mission_contract.v0"

    def canonical_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("mission_hash", None)
        return payload

    def mission_hash(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        payload = self.canonical_payload()
        payload["mission_hash"] = self.mission_hash()
        return payload


def create_mission_contract(
    *,
    mission_id: str,
    mission_goal: str,
    business_id: str,
    creator_id: str,
    human_checkpoints: list[MissionCheckpoint] | None = None,
) -> AionMissionContract:
    return AionMissionContract(
        mission_id=mission_id,
        mission_goal=mission_goal,
        business_id=business_id,
        creator_id=creator_id,
        human_checkpoints=tuple(human_checkpoints or ()),
    )


def validate_no_live_side_effects(contract: AionMissionContract) -> bool:
    return not any(
        [
            contract.live_external_writes_enabled,
            contract.live_payment_enabled,
            contract.live_booking_enabled,
            contract.live_deployment_enabled,
            contract.live_reputation_mutation_enabled,
            contract.live_chain_write_enabled,
        ]
    )
