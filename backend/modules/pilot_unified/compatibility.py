from __future__ import annotations

import re
from typing import Any, Mapping

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso

from .contracts import (
    ActionProposal,
    ActionState,
    DeviceRef,
    MessageEnvelope,
    MessageKind,
    PersonRef,
    PrivacyLevel,
    SpaceKind,
    SpaceRef,
)


def _value(record: Mapping[str, Any], key: str, fallback: str = "") -> str:
    return str(record.get(key) or fallback)


def adapt_private_profile(record: Mapping[str, Any]) -> PersonRef:
    persona_id = _value(record, "persona_id")
    return PersonRef(
        person_id=f"person/{persona_id}",
        persona_id=persona_id,
        display_name=_value(record, "display_name", "Pilot user"),
        role=_value(record, "role", "adult"),
        status=_value(record, "status", "active"),
        guardian_persona_id=record.get("guardian_persona_id") or None,
    )


def adapt_private_device(record: Mapping[str, Any]) -> DeviceRef:
    public_key = _value(record, "public_key")
    return DeviceRef(
        device_id=_value(record, "device_id"),
        persona_id=_value(record, "persona_id"),
        label=_value(record, "device_label", "Phone"),
        status=_value(record, "status", "unknown"),
        possession_verified=bool(record.get("possession_verified")),
        public_key_fingerprint=canonical_hash(public_key)[:32] if public_key else "",
    )


def personal_space(persona_id: str, display_name: str) -> SpaceRef:
    return SpaceRef(
        space_id=f"personal/{persona_id}",
        kind=SpaceKind.PERSONAL,
        display_name=f"{display_name} — Personal",
        owner_ref=persona_id,
        policy_ref="pilot.personal.default.v1",
    )


def adapt_workspace(record: Mapping[str, Any]) -> SpaceRef:
    owner = _value(record, "owner")
    # Legacy business records may use an owner display name (for example
    # ``Kevin Robinson``).  A mobile capability contract requires a stable,
    # non-display identifier, so retain valid refs and derive a non-reversible
    # local reference for older records.
    owner_ref = owner if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,199}", owner) else f"owner/{canonical_hash(owner)[:24]}"
    return SpaceRef(
        space_id=f"workspace/{_value(record, 'id')}",
        kind=SpaceKind.BOARDROOM if _value(record, "business_type").lower() == "boardroom" else SpaceKind.WORKSPACE,
        display_name=_value(record, "name", "Workspace"),
        owner_ref=owner_ref,
        policy_ref=_value(record, "governance_policy_ref"),
        status=_value(record, "status", "active"),
    )


def adapt_workspace_bundle(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project Boardroom declarations without manufacturing mobile authority."""
    return {
        "space": adapt_workspace(record),
        "declared_role_ids": tuple(str(item) for item in record.get("role_ids", []) if str(item)),
        "declared_container_ids": tuple(str(item) for item in record.get("container_ids", []) if str(item)),
        "declared_tool_connections": tuple(str(item) for item in record.get("tool_connections", []) if str(item)),
        "granted_capabilities": (),
        "requires_signed_workspace_manifest": True,
        "source_schema": "aion_business.workspace",
    }


_TASK_STATE = {
    "awaiting_recipient_acceptance": ActionState.DELIVERED,
    "pending_external_delivery_approval": ActionState.AWAITING_APPROVAL,
    "awaiting_external_delivery_adapter": ActionState.APPROVED,
    "open": ActionState.ACCEPTED,
    "snoozed": ActionState.ACCEPTED,
    "completed": ActionState.VERIFIED,
    "declined": ActionState.DECLINED,
    "cancelled": ActionState.CANCELLED,
}


def adapt_pilot_task(record: Mapping[str, Any], *, space_id: str | None = None) -> ActionProposal:
    owner = _value(record, "owner_persona_id")
    scope = {
        "title": _value(record, "title"),
        "notes": _value(record, "notes"),
        "list_id": record.get("list_id"),
        "assignee_persona_id": record.get("assignee_persona_id"),
    }
    return ActionProposal(
        action_id=_value(record, "task_id"),
        space_id=space_id or f"personal/{owner}",
        owner_persona_id=owner,
        requester_persona_id=_value(record, "requester_persona_id", owner),
        assignee_persona_id=record.get("assignee_persona_id") or None,
        action_type="task",
        state=_TASK_STATE.get(_value(record, "status"), ActionState.DRAFT),
        scope_hash=canonical_hash(scope),
        created_at=_value(record, "created_at", utc_now_iso()),
        source_ref=_value(record.get("source") or {}, "surface"),
        requires_recipient_acceptance=bool(record.get("recipient_acceptance_required")),
    )


def adapt_pilot_message(record: Mapping[str, Any], *, space_id: str | None = None) -> MessageEnvelope:
    sender = _value(record, "sender_persona_id")
    recipient = _value(record, "recipient_persona_id")
    body = _value(record, "body")
    message_id = _value(record, "message_id")
    kind = MessageKind.TASK_PROPOSAL if _value(record, "kind") == "task_request" else MessageKind.TEXT
    return MessageEnvelope(
        message_id=message_id,
        conversation_id=f"conversation/{min(sender, recipient)}--{max(sender, recipient)}",
        space_id=space_id or f"personal/{sender}",
        sender_persona_id=sender,
        recipient_ids=(recipient,),
        kind=kind,
        privacy=PrivacyLevel.PRIVATE,
        created_at=_value(record, "created_at", utc_now_iso()),
        idempotency_key=f"legacy/{message_id}",
        content_hash=canonical_hash(body),
        object_ref=_value(record, "object_id"),
        source_schema="pilot.inbox.v1",
    )


def adapt_private_contact(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return route references for the owning persona without resolving authority."""
    owner = _value(record, "owner_persona_id")
    return {
        "contact_id": _value(record, "contact_id"),
        "owner_persona_id": owner,
        "display_name": _value(record, "display_name"),
        "available_routes": tuple(
            route for route, field in (("pilot", "pilot_persona_id"), ("whatsapp", "whatsapp"), ("email", "email"))
            if _value(record, field)
        ),
        "preferred_route": _value(record, "preferred_route"),
        "source_schema": "pilot.inbox.v1",
        "authority_granted": False,
    }


def adapt_legacy_communication_draft(record: Mapping[str, Any], *, space_id: str | None = None) -> dict[str, Any]:
    """Legacy approval is never promoted without a new possession-bound proof."""
    persona = _value(record, "persona_id")
    scope = {
        "recipient_hash": canonical_hash(_value(record, "recipient")),
        "subject_hash": canonical_hash(_value(record, "subject")),
        "body_hash": canonical_hash(_value(record, "body")),
        "channel": _value(record, "channel"),
    }
    proposal = ActionProposal(
        action_id=_value(record, "draft_id"),
        space_id=space_id or f"personal/{persona}",
        owner_persona_id=persona,
        requester_persona_id=persona,
        action_type="communication.send",
        state=ActionState.AWAITING_APPROVAL,
        scope_hash=canonical_hash(scope),
        created_at=_value(record, "created_at", utc_now_iso()),
        source_ref="pilot.communication.v1",
    )
    return {
        "proposal": proposal,
        "approval": None,
        "legacy_status": _value(record, "status"),
        "legacy_approval_requires_reconfirmation": True,
        "plaintext_in_projection": False,
    }


def adapt_glyphnet_event(record: Mapping[str, Any], *, space_id: str) -> MessageEnvelope:
    event_id = _value(record, "id")
    sender = _value(record, "from")
    recipient = _value(record, "to")
    event_type = _value(record, "type", "text")
    payload = dict(record.get("payload") or {})
    kind = {
        "voice_note": MessageKind.VOICE_NOTE,
        "voice_frame": MessageKind.PTT,
        "voice_offer": MessageKind.CALL_SIGNAL,
        "voice_answer": MessageKind.CALL_SIGNAL,
        "ice": MessageKind.CALL_SIGNAL,
    }.get(event_type, MessageKind.TEXT)
    return MessageEnvelope(
        message_id=f"glyphnet/{event_id}",
        conversation_id=f"conversation/{min(sender, recipient)}--{max(sender, recipient)}",
        space_id=space_id,
        sender_persona_id=sender,
        recipient_ids=(recipient,),
        kind=kind,
        privacy=PrivacyLevel.PRIVATE,
        created_at=_value(record, "ts", utc_now_iso()),
        idempotency_key=f"glyphnet/{event_id}",
        content_hash=canonical_hash(payload),
        source_schema="glyphnet.threadlog.v1",
    )


def adapt_private_identity_snapshot(state: Mapping[str, Any]) -> dict[str, tuple[Any, ...]]:
    """Return immutable projections; never modify or rewrite the source store."""
    people = tuple(adapt_private_profile(item) for item in state.get("profiles", []) if isinstance(item, Mapping))
    devices = tuple(adapt_private_device(item) for item in state.get("devices", []) if isinstance(item, Mapping))
    spaces = tuple(personal_space(person.persona_id, person.display_name) for person in people)
    return {"people": people, "devices": devices, "spaces": spaces}
