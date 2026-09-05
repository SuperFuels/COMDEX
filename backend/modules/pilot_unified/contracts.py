from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence

from backend.modules.aion_fabric.canonical import canonical_hash


CONTRACT_VERSION = "pilot.unified.v1"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,199}$")


class SpaceKind(str, Enum):
    PERSONAL = "personal"
    HOUSEHOLD = "household"
    WORKSPACE = "workspace"
    ENGAGEMENT = "engagement"
    BOARDROOM = "boardroom"


class PrivacyLevel(str, Enum):
    PRIVATE = "private"
    HOUSEHOLD_SHARED = "household_shared"
    WORKSPACE = "workspace"
    ORGANISATION = "organisation"


class MessageKind(str, Enum):
    TEXT = "text"
    VOICE_NOTE = "voice_note"
    PTT = "ptt"
    CALL_SIGNAL = "call_signal"
    TASK_PROPOSAL = "task_proposal"
    APPROVAL = "approval"
    REMINDER = "reminder"
    CALENDAR = "calendar"
    DOCUMENT_REVIEW = "document_review"
    DELEGATION = "delegation"
    PROVIDER_HANDOFF = "provider_handoff"


class ActionState(str, Enum):
    DRAFT = "draft"
    NEEDS_DETAILS = "needs_details"
    PREPARED = "prepared"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    QUEUED = "queued"
    DELIVERED = "delivered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXECUTING = "executing"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InvitationState(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REVOKED = "revoked"
    EXPIRED = "expired"


_TRANSITIONS: Mapping[ActionState, frozenset[ActionState]] = {
    ActionState.DRAFT: frozenset({ActionState.NEEDS_DETAILS, ActionState.PREPARED, ActionState.CANCELLED}),
    ActionState.NEEDS_DETAILS: frozenset({ActionState.PREPARED, ActionState.CANCELLED, ActionState.EXPIRED}),
    ActionState.PREPARED: frozenset({ActionState.AWAITING_APPROVAL, ActionState.QUEUED, ActionState.CANCELLED, ActionState.EXPIRED}),
    ActionState.AWAITING_APPROVAL: frozenset({ActionState.APPROVED, ActionState.DECLINED, ActionState.CANCELLED, ActionState.EXPIRED}),
    ActionState.APPROVED: frozenset({ActionState.QUEUED, ActionState.EXECUTING, ActionState.CANCELLED, ActionState.EXPIRED}),
    ActionState.QUEUED: frozenset({ActionState.DELIVERED, ActionState.EXECUTING, ActionState.FAILED, ActionState.CANCELLED, ActionState.EXPIRED}),
    ActionState.DELIVERED: frozenset({ActionState.ACCEPTED, ActionState.DECLINED, ActionState.VERIFIED, ActionState.FAILED, ActionState.EXPIRED}),
    ActionState.ACCEPTED: frozenset({ActionState.EXECUTING, ActionState.VERIFIED, ActionState.CANCELLED}),
    ActionState.EXECUTING: frozenset({ActionState.VERIFIED, ActionState.FAILED, ActionState.CANCELLED}),
    ActionState.FAILED: frozenset({ActionState.QUEUED, ActionState.CANCELLED}),
    ActionState.DECLINED: frozenset(),
    ActionState.VERIFIED: frozenset(),
    ActionState.CANCELLED: frozenset(),
    ActionState.EXPIRED: frozenset(),
}


def assert_transition(current: ActionState, target: ActionState) -> None:
    if target == current:
        return
    if target not in _TRANSITIONS[current]:
        raise ValueError(f"Invalid action transition: {current.value} -> {target.value}")


def _require_id(value: str, label: str) -> None:
    if not _ID.fullmatch(str(value or "")):
        raise ValueError(f"{label} is not a valid bounded identifier")


def _require_time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from None
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _bounded_text(value: str, label: str, maximum: int) -> None:
    if len(str(value)) > maximum:
        raise ValueError(f"{label} exceeds {maximum} characters")


@dataclass(frozen=True, slots=True)
class Contract:
    schema_version: str = field(default=CONTRACT_VERSION, init=False)

    def to_dict(self) -> dict[str, Any]:
        def normalize(value: Any) -> Any:
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, tuple):
                return [normalize(item) for item in value]
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            if isinstance(value, list):
                return [normalize(item) for item in value]
            return value

        return normalize(asdict(self))

    def contract_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True, slots=True)
class PersonRef(Contract):
    person_id: str
    persona_id: str
    display_name: str
    role: str
    status: str = "active"
    guardian_persona_id: str | None = None

    def __post_init__(self) -> None:
        _require_id(self.person_id, "person_id")
        _require_id(self.persona_id, "persona_id")
        _bounded_text(self.display_name, "display_name", 80)
        if not self.display_name.strip():
            raise ValueError("display_name is required")


@dataclass(frozen=True, slots=True)
class DeviceRef(Contract):
    device_id: str
    persona_id: str
    label: str
    status: str
    possession_verified: bool
    public_key_fingerprint: str = ""

    def __post_init__(self) -> None:
        _require_id(self.device_id, "device_id")
        _require_id(self.persona_id, "persona_id")
        _bounded_text(self.label, "label", 80)


@dataclass(frozen=True, slots=True)
class PossessionProof(Contract):
    proof_id: str
    device_id: str
    persona_id: str
    purpose: str
    challenge_hash: str
    signature: str
    issued_at: str
    expires_at: str

    def __post_init__(self) -> None:
        for label in ("proof_id", "device_id", "persona_id", "purpose"):
            _require_id(getattr(self, label), label)
        if not re.fullmatch(r"[0-9a-f]{64}", self.challenge_hash):
            raise ValueError("challenge_hash must be a SHA-256 hex digest")
        if not self.signature:
            raise ValueError("signature is required")
        if _require_time(self.expires_at, "expires_at") <= _require_time(self.issued_at, "issued_at"):
            raise ValueError("possession proof expiry must follow issue time")


@dataclass(frozen=True, slots=True)
class SpaceRef(Contract):
    space_id: str
    kind: SpaceKind
    display_name: str
    owner_ref: str
    policy_ref: str = ""
    status: str = "active"

    def __post_init__(self) -> None:
        _require_id(self.space_id, "space_id")
        _require_id(self.owner_ref, "owner_ref")
        _bounded_text(self.display_name, "display_name", 120)


@dataclass(frozen=True, slots=True)
class Membership(Contract):
    membership_id: str
    persona_id: str
    space_id: str
    role_id: str
    scopes: tuple[str, ...]
    status: str
    issued_at: str
    expires_at: str | None = None
    revision: int = 1

    def __post_init__(self) -> None:
        for label in ("membership_id", "persona_id", "space_id", "role_id"):
            _require_id(getattr(self, label), label)
        _require_time(self.issued_at, "issued_at")
        if self.expires_at and _require_time(self.expires_at, "expires_at") <= _require_time(self.issued_at, "issued_at"):
            raise ValueError("membership expiry must follow issue time")
        if self.revision < 1:
            raise ValueError("membership revision must be positive")

    def is_active(self, *, now: datetime | None = None) -> bool:
        if self.status != "active":
            return False
        if not self.expires_at:
            return True
        check = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return _require_time(self.expires_at, "expires_at") > check


@dataclass(frozen=True, slots=True)
class Invitation(Contract):
    invitation_id: str
    space_id: str
    inviter_persona_id: str
    recipient_ref: str
    role_id: str
    requested_scopes: tuple[str, ...]
    state: InvitationState
    created_at: str
    expires_at: str
    accepted_by_persona_id: str | None = None
    revoked_at: str | None = None

    def __post_init__(self) -> None:
        for label in ("invitation_id", "space_id", "inviter_persona_id", "recipient_ref", "role_id"):
            _require_id(getattr(self, label), label)
        if _require_time(self.expires_at, "expires_at") <= _require_time(self.created_at, "created_at"):
            raise ValueError("invitation expiry must follow creation")
        if self.state == InvitationState.ACCEPTED and not self.accepted_by_persona_id:
            raise ValueError("accepted invitation requires the accepting persona")
        if self.state == InvitationState.REVOKED and not self.revoked_at:
            raise ValueError("revoked invitation requires a revocation timestamp")


@dataclass(frozen=True, slots=True)
class CapabilityLease(Contract):
    lease_id: str
    persona_id: str
    device_id: str
    space_id: str
    membership_id: str
    scopes: tuple[str, ...]
    issued_at: str
    expires_at: str
    nonce: str
    issuer_id: str

    def __post_init__(self) -> None:
        for label in ("lease_id", "persona_id", "device_id", "space_id", "membership_id", "nonce", "issuer_id"):
            _require_id(getattr(self, label), label)
        if _require_time(self.expires_at, "expires_at") <= _require_time(self.issued_at, "issued_at"):
            raise ValueError("lease expiry must follow issue time")

    def permits(self, scope: str, *, now: datetime | None = None) -> bool:
        check = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return scope in self.scopes and _require_time(self.expires_at, "expires_at") > check


@dataclass(frozen=True, slots=True)
class ActiveContext(Contract):
    persona_id: str
    device_id: str
    mother_id: str
    space_id: str
    role_id: str
    membership_id: str
    lease_id: str
    privacy: PrivacyLevel
    expires_at: str

    def __post_init__(self) -> None:
        for label in ("persona_id", "device_id", "mother_id", "space_id", "role_id", "membership_id", "lease_id"):
            _require_id(getattr(self, label), label)
        _require_time(self.expires_at, "expires_at")


@dataclass(frozen=True, slots=True)
class Participant(Contract):
    participant_id: str
    persona_id: str
    role: str = "member"

    def __post_init__(self) -> None:
        _require_id(self.participant_id, "participant_id")
        _require_id(self.persona_id, "persona_id")


@dataclass(frozen=True, slots=True)
class Conversation(Contract):
    conversation_id: str
    space_id: str
    participant_ids: tuple[str, ...]
    privacy: PrivacyLevel
    created_at: str

    def __post_init__(self) -> None:
        _require_id(self.conversation_id, "conversation_id")
        _require_id(self.space_id, "space_id")
        _require_time(self.created_at, "created_at")
        if not self.participant_ids:
            raise ValueError("conversation requires at least one participant")


@dataclass(frozen=True, slots=True)
class AttachmentRef(Contract):
    attachment_id: str
    owner_persona_id: str
    storage_ref: str
    media_type: str
    byte_length: int
    content_hash: str
    encrypted: bool = True

    def __post_init__(self) -> None:
        for label in ("attachment_id", "owner_persona_id", "storage_ref"):
            _require_id(getattr(self, label), label)
        if self.byte_length < 0 or self.byte_length > 25_000_000:
            raise ValueError("attachment size is outside the supported bound")
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_hash):
            raise ValueError("content_hash must be a SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class MessageEnvelope(Contract):
    message_id: str
    conversation_id: str
    space_id: str
    sender_persona_id: str
    recipient_ids: tuple[str, ...]
    kind: MessageKind
    privacy: PrivacyLevel
    created_at: str
    idempotency_key: str
    content_hash: str
    encrypted_payload: str = ""
    object_ref: str = ""
    reply_to: str = ""
    expires_at: str | None = None
    source_schema: str = ""
    attachment_refs: tuple[str, ...] = ()
    correction_of: str = ""
    supersedes: str = ""

    def __post_init__(self) -> None:
        for label in ("message_id", "conversation_id", "space_id", "sender_persona_id", "idempotency_key"):
            _require_id(getattr(self, label), label)
        _require_time(self.created_at, "created_at")
        if self.expires_at:
            _require_time(self.expires_at, "expires_at")
        if not self.recipient_ids:
            raise ValueError("message requires a recipient")
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_hash):
            raise ValueError("content_hash must be a SHA-256 hex digest")
        if self.encrypted_payload and len(self.encrypted_payload) > 1_400_000:
            raise ValueError("encrypted payload exceeds the envelope limit")


@dataclass(frozen=True, slots=True)
class ActionProposal(Contract):
    action_id: str
    space_id: str
    owner_persona_id: str
    requester_persona_id: str
    action_type: str
    state: ActionState
    scope_hash: str
    created_at: str
    assignee_persona_id: str | None = None
    source_ref: str = ""
    requires_recipient_acceptance: bool = False

    def __post_init__(self) -> None:
        for label in ("action_id", "space_id", "owner_persona_id", "requester_persona_id"):
            _require_id(getattr(self, label), label)
        _require_time(self.created_at, "created_at")
        if not re.fullmatch(r"[0-9a-f]{64}", self.scope_hash):
            raise ValueError("scope_hash must be a SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class ApprovalRecord(Contract):
    approval_id: str
    action_id: str
    space_id: str
    approver_persona_id: str
    scope_hash: str
    decision: str
    decided_at: str
    device_id: str
    possession_proof_ref: str

    def __post_init__(self) -> None:
        for label in ("approval_id", "action_id", "space_id", "approver_persona_id", "device_id", "possession_proof_ref"):
            _require_id(getattr(self, label), label)
        if self.decision not in {"approved", "declined"}:
            raise ValueError("approval decision must be approved or declined")
        if not re.fullmatch(r"[0-9a-f]{64}", self.scope_hash):
            raise ValueError("scope_hash must be a SHA-256 hex digest")
        _require_time(self.decided_at, "decided_at")


@dataclass(frozen=True, slots=True)
class ExecutionRecord(Contract):
    execution_id: str
    action_id: str
    space_id: str
    adapter_id: str
    attempt: int
    state: ActionState
    scope_hash: str
    started_at: str
    finished_at: str | None = None
    provider_receipt_ref: str = ""

    def __post_init__(self) -> None:
        for label in ("execution_id", "action_id", "space_id", "adapter_id"):
            _require_id(getattr(self, label), label)
        if self.attempt < 1:
            raise ValueError("execution attempt must be positive")
        if not re.fullmatch(r"[0-9a-f]{64}", self.scope_hash):
            raise ValueError("scope_hash must be a SHA-256 hex digest")
        started = _require_time(self.started_at, "started_at")
        if self.finished_at and _require_time(self.finished_at, "finished_at") < started:
            raise ValueError("execution finish cannot precede its start")


@dataclass(frozen=True, slots=True)
class ActionReceipt(Contract):
    receipt_id: str
    action_id: str
    space_id: str
    actor_persona_id: str
    state: ActionState
    scope_hash: str
    result_hash: str
    recorded_at: str
    provider_receipt_ref: str = ""
    verified: bool = False

    def __post_init__(self) -> None:
        for label in ("receipt_id", "action_id", "space_id", "actor_persona_id"):
            _require_id(getattr(self, label), label)
        _require_time(self.recorded_at, "recorded_at")
        for label in ("scope_hash", "result_hash"):
            if not re.fullmatch(r"[0-9a-f]{64}", getattr(self, label)):
                raise ValueError(f"{label} must be a SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class SurfaceManifest(Contract):
    manifest_id: str
    surface_id: str
    persona_id: str
    space_id: str
    lease_id: str
    capabilities: tuple[str, ...]
    redactions: tuple[str, ...]
    issued_at: str
    expires_at: str

    def __post_init__(self) -> None:
        for label in ("manifest_id", "surface_id", "persona_id", "space_id", "lease_id"):
            _require_id(getattr(self, label), label)
        if _require_time(self.expires_at, "expires_at") <= _require_time(self.issued_at, "issued_at"):
            raise ValueError("manifest expiry must follow issue time")


@dataclass(frozen=True, slots=True)
class ServiceConnectionRef(Contract):
    connection_id: str
    persona_id: str
    service: str
    scopes: tuple[str, ...]
    status: str
    credential_ref: str

    def __post_init__(self) -> None:
        _require_id(self.connection_id, "connection_id")
        _require_id(self.persona_id, "persona_id")
        _require_id(self.credential_ref, "credential_ref")


@dataclass(frozen=True, slots=True)
class MemoryItemRef(Contract):
    memory_id: str
    owner_persona_id: str
    space_id: str
    scope: PrivacyLevel
    kind: str
    content_hash: str
    storage_ref: str
    created_at: str

    def __post_init__(self) -> None:
        for label in ("memory_id", "owner_persona_id", "space_id", "kind", "storage_ref"):
            _require_id(getattr(self, label), label)
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_hash):
            raise ValueError("content_hash must be a SHA-256 hex digest")
        _require_time(self.created_at, "created_at")


def typed_object_key(kind: str, identifier: str) -> str:
    """Prevent unrelated legacy objects with the same raw ID from colliding."""
    _require_id(kind, "kind")
    _require_id(identifier, "identifier")
    return f"{kind}:{identifier}"


def validate_active_context(
    context: ActiveContext,
    membership: Membership,
    lease: CapabilityLease,
    *,
    required_scope: str,
    now: datetime | None = None,
) -> None:
    check = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if _require_time(context.expires_at, "expires_at") <= check:
        raise PermissionError("Active context expired")
    if not membership.is_active(now=check):
        raise PermissionError("Membership is not active")
    if not lease.permits(required_scope, now=check):
        raise PermissionError("Capability lease does not permit this operation")
    expected = (context.persona_id, context.space_id, context.membership_id)
    if expected != (membership.persona_id, membership.space_id, membership.membership_id):
        raise PermissionError("Active context does not match membership")
    if context.role_id != membership.role_id:
        raise PermissionError("Active context role does not match membership")
    if (context.persona_id, context.device_id, context.space_id, context.membership_id, context.lease_id) != (
        lease.persona_id,
        lease.device_id,
        lease.space_id,
        lease.membership_id,
        lease.lease_id,
    ):
        raise PermissionError("Active context does not match capability lease")


def validate_message_authority(context: ActiveContext, envelope: MessageEnvelope) -> None:
    if context.persona_id != envelope.sender_persona_id:
        raise PermissionError("Message sender does not match the active identity")
    if context.space_id != envelope.space_id:
        raise PermissionError("Message space does not match the active context")


class ReplayGuard:
    """Bounded in-memory replay detector for tests and single-process adapters.

    Production transports must back this contract with durable expiry-aware state.
    """

    def __init__(self, maximum: int = 4096) -> None:
        if maximum < 1:
            raise ValueError("maximum must be positive")
        self.maximum = maximum
        self._seen: dict[str, None] = {}

    def accept(self, key: str) -> None:
        _require_id(key, "idempotency_key")
        if key in self._seen:
            raise PermissionError("Replay detected")
        self._seen[key] = None
        while len(self._seen) > self.maximum:
            self._seen.pop(next(iter(self._seen)))
