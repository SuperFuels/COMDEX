from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from backend.modules.aion_fabric.canonical import canonical_hash
from backend.modules.pilot_unified.compatibility import (
    adapt_glyphnet_event,
    adapt_legacy_communication_draft,
    adapt_pilot_message,
    adapt_pilot_task,
    adapt_private_contact,
    adapt_private_identity_snapshot,
    adapt_workspace,
    adapt_workspace_bundle,
)
from backend.modules.pilot_unified.contracts import (
    CONTRACT_VERSION,
    ActionState,
    ActiveContext,
    ApprovalRecord,
    AttachmentRef,
    CapabilityLease,
    ExecutionRecord,
    Invitation,
    InvitationState,
    Membership,
    MemoryItemRef,
    MessageEnvelope,
    MessageKind,
    PrivacyLevel,
    PossessionProof,
    ReplayGuard,
    assert_transition,
    typed_object_key,
    validate_active_context,
    validate_message_authority,
)
from backend.modules.pilot_unified.feature_policy import DEFAULT_MOBILE_FEATURE_POLICY


NOW = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)


def iso(delta_minutes: int) -> str:
    return (NOW + timedelta(minutes=delta_minutes)).isoformat()


def authority_fixture(*, space_id: str = "personal/persona_alice", expires: int = 10):
    membership = Membership(
        membership_id="membership_alice",
        persona_id="persona_alice",
        space_id=space_id,
        role_id="role_owner",
        scopes=("message.send",),
        status="active",
        issued_at=iso(-10),
        expires_at=iso(60),
    )
    lease = CapabilityLease(
        lease_id="lease_alice",
        persona_id="persona_alice",
        device_id="phone_alice",
        space_id=space_id,
        membership_id=membership.membership_id,
        scopes=("message.send",),
        issued_at=iso(-5),
        expires_at=iso(expires),
        nonce="nonce_alice",
        issuer_id="mother_alice",
    )
    context = ActiveContext(
        persona_id="persona_alice",
        device_id="phone_alice",
        mother_id="mother_alice",
        space_id=space_id,
        role_id="role_owner",
        membership_id=membership.membership_id,
        lease_id=lease.lease_id,
        privacy=PrivacyLevel.PRIVATE,
        expires_at=iso(expires),
    )
    return context, membership, lease


def message(*, space_id: str = "personal/persona_alice", sender: str = "persona_alice") -> MessageEnvelope:
    return MessageEnvelope(
        message_id="message_1",
        conversation_id="conversation_alice--bob",
        space_id=space_id,
        sender_persona_id=sender,
        recipient_ids=("persona_bob",),
        kind=MessageKind.TEXT,
        privacy=PrivacyLevel.PRIVATE,
        created_at=iso(0),
        idempotency_key="send_1",
        content_hash=canonical_hash("hello"),
    )


def test_contracts_are_versioned_and_hash_deterministically():
    first = message()
    second = message()
    assert first.schema_version == CONTRACT_VERSION
    assert first.to_dict()["kind"] == "text"
    assert first.contract_hash() == second.contract_hash()


def test_active_context_requires_matching_person_space_membership_lease_and_scope():
    context, membership, lease = authority_fixture()
    validate_active_context(context, membership, lease, required_scope="message.send", now=NOW)
    wrong_space, _, _ = authority_fixture(space_id="workspace/acme")
    with pytest.raises(PermissionError, match="does not match membership"):
        validate_active_context(wrong_space, membership, lease, required_scope="message.send", now=NOW)
    with pytest.raises(PermissionError, match="does not permit"):
        validate_active_context(context, membership, lease, required_scope="finance.approve", now=NOW)


def test_expired_context_and_lease_fail_closed():
    context, membership, lease = authority_fixture(expires=-1)
    with pytest.raises(PermissionError, match="expired"):
        validate_active_context(context, membership, lease, required_scope="message.send", now=NOW)


def test_message_cannot_cross_person_or_space():
    context, _, _ = authority_fixture()
    validate_message_authority(context, message())
    with pytest.raises(PermissionError, match="sender"):
        validate_message_authority(context, message(sender="persona_mallory"))
    with pytest.raises(PermissionError, match="space"):
        validate_message_authority(context, message(space_id="workspace/acme"))


def test_replay_guard_rejects_duplicate_and_is_bounded():
    guard = ReplayGuard(maximum=2)
    guard.accept("one")
    with pytest.raises(PermissionError, match="Replay"):
        guard.accept("one")
    guard.accept("two")
    guard.accept("three")
    guard.accept("one")


def test_typed_keys_prevent_legacy_identifier_collision():
    assert typed_object_key("task", "same") != typed_object_key("message", "same")


def test_state_machine_rejects_false_completion():
    assert_transition(ActionState.DELIVERED, ActionState.ACCEPTED)
    assert_transition(ActionState.EXECUTING, ActionState.VERIFIED)
    with pytest.raises(ValueError, match="Invalid action transition"):
        assert_transition(ActionState.DRAFT, ActionState.VERIFIED)
    with pytest.raises(ValueError, match="Invalid action transition"):
        assert_transition(ActionState.PREPARED, ActionState.DELIVERED)


def test_invitation_possession_and_action_records_are_explicitly_versioned():
    invitation = Invitation(
        invitation_id="invite_1", space_id="workspace/acme", inviter_persona_id="persona_alice",
        recipient_ref="contact_bob", role_id="role_marketing", requested_scopes=("briefing.read",),
        state=InvitationState.PENDING, created_at=iso(0), expires_at=iso(60),
    )
    proof = PossessionProof(
        proof_id="proof_1", device_id="phone_alice", persona_id="persona_alice",
        purpose="action.approve", challenge_hash=canonical_hash("challenge"), signature="signed",
        issued_at=iso(0), expires_at=iso(5),
    )
    approval = ApprovalRecord(
        approval_id="approval_1", action_id="task_1", space_id="workspace/acme",
        approver_persona_id="persona_alice", scope_hash=canonical_hash("scope"),
        decision="approved", decided_at=iso(1), device_id="phone_alice",
        possession_proof_ref=proof.proof_id,
    )
    execution = ExecutionRecord(
        execution_id="execution_1", action_id="task_1", space_id="workspace/acme",
        adapter_id="adapter_tasks", attempt=1, state=ActionState.EXECUTING,
        scope_hash=approval.scope_hash, started_at=iso(2),
    )
    assert invitation.schema_version == CONTRACT_VERSION
    assert proof.schema_version == CONTRACT_VERSION
    assert approval.scope_hash == execution.scope_hash


def test_attachment_and_memory_are_refs_not_embedded_private_content():
    attachment = AttachmentRef(
        attachment_id="attachment_1", owner_persona_id="persona_alice",
        storage_ref="vault/attachment_1", media_type="application/pdf", byte_length=100,
        content_hash=canonical_hash("pdf"),
    )
    memory = MemoryItemRef(
        memory_id="memory_1", owner_persona_id="persona_alice", space_id="personal/persona_alice",
        scope=PrivacyLevel.PRIVATE, kind="preference", content_hash=canonical_hash("private"),
        storage_ref="vault/memory_1", created_at=iso(0),
    )
    assert attachment.encrypted is True
    assert "content" not in memory.to_dict()
    assert memory.storage_ref == "vault/memory_1"


def test_private_identity_compatibility_projection_is_immutable_and_redacts_public_key():
    source = {
        "profiles": [{"persona_id": "persona_alice", "display_name": "Alice", "role": "adult", "status": "active"}],
        "devices": [{"device_id": "phone_alice", "persona_id": "persona_alice", "device_label": "Alice phone", "status": "trusted", "possession_verified": True, "public_key": "secret-public-material"}],
    }
    projection = adapt_private_identity_snapshot(source)
    assert projection["people"][0].display_name == "Alice"
    assert projection["spaces"][0].space_id == "personal/persona_alice"
    assert projection["devices"][0].public_key_fingerprint
    assert "public_key" not in projection["devices"][0].to_dict()
    assert source["profiles"][0].get("person_id") is None


def test_pilot_inbox_compatibility_preserves_provenance_and_acceptance():
    task = adapt_pilot_task({
        "task_id": "task_1", "owner_persona_id": "persona_alice",
        "requester_persona_id": "persona_alice", "assignee_persona_id": "persona_bob",
        "title": "Collect dry cleaning", "status": "awaiting_recipient_acceptance",
        "recipient_acceptance_required": True, "created_at": iso(0),
    })
    assert task.state == ActionState.DELIVERED
    assert task.requires_recipient_acceptance is True
    legacy = adapt_pilot_message({
        "message_id": "message_legacy", "sender_persona_id": "persona_alice",
        "recipient_persona_id": "persona_bob", "body": "Task request: Collect dry cleaning",
        "kind": "task_request", "object_id": "task_1", "created_at": iso(0),
    })
    assert legacy.kind == MessageKind.TASK_PROPOSAL
    assert legacy.source_schema == "pilot.inbox.v1"


def test_glyphnet_and_boardroom_are_adapted_without_claiming_extra_authority():
    glyph = adapt_glyphnet_event({
        "id": 12, "type": "voice_note", "ts": iso(0), "from": "persona_alice",
        "to": "persona_bob", "payload": {"blob_ref": "private/blob/12"},
    }, space_id="personal/persona_alice")
    assert glyph.kind == MessageKind.VOICE_NOTE
    assert glyph.source_schema == "glyphnet.threadlog.v1"
    workspace = adapt_workspace({
        "id": "acme", "name": "Acme", "business_type": "company", "owner": "org_acme",
        "governance_policy_ref": "policy_acme", "status": "active",
    })
    assert workspace.space_id == "workspace/acme"
    assert workspace.kind.value == "workspace"
    bundle = adapt_workspace_bundle({
        "id": "acme", "name": "Acme", "business_type": "company", "owner": "org_acme",
        "role_ids": ["role_marketing"], "tool_connections": ["crm"],
    })
    assert bundle["declared_role_ids"] == ("role_marketing",)
    assert bundle["granted_capabilities"] == ()
    assert bundle["requires_signed_workspace_manifest"] is True


def test_contact_projection_and_legacy_approval_do_not_grant_authority():
    contact = adapt_private_contact({
        "contact_id": "contact_bob", "owner_persona_id": "persona_alice",
        "display_name": "Bob", "pilot_persona_id": "persona_bob", "email": "bob@example.test",
        "preferred_route": "pilot",
    })
    assert contact["available_routes"] == ("pilot", "email")
    assert contact["authority_granted"] is False
    adapted = adapt_legacy_communication_draft({
        "draft_id": "communication_1", "persona_id": "persona_alice", "recipient": "bob@example.test",
        "subject": "Hello", "body": "Private legacy content", "channel": "email",
        "status": "approved_pending_adapter", "created_at": iso(0),
    })
    assert adapted["proposal"].state == ActionState.AWAITING_APPROVAL
    assert adapted["approval"] is None
    assert adapted["legacy_approval_requires_reconfirmation"] is True
    assert "Private legacy content" not in str(adapted)


def test_malicious_or_oversized_envelopes_fail_before_delivery():
    with pytest.raises(ValueError, match="identifier"):
        MessageEnvelope(
            message_id="../../escape", conversation_id="conversation_1",
            space_id="personal/persona_alice", sender_persona_id="persona_alice",
            recipient_ids=("persona_bob",), kind=MessageKind.TEXT, privacy=PrivacyLevel.PRIVATE,
            created_at=iso(0), idempotency_key="send_unsafe", content_hash=canonical_hash("x"),
        )
    with pytest.raises(ValueError, match="envelope limit"):
        MessageEnvelope(
            message_id="message_big", conversation_id="conversation_1",
            space_id="personal/persona_alice", sender_persona_id="persona_alice",
            recipient_ids=("persona_bob",), kind=MessageKind.TEXT, privacy=PrivacyLevel.PRIVATE,
            created_at=iso(0), idempotency_key="send_big", content_hash=canonical_hash("x"),
            encrypted_payload="x" * 1_400_001,
        )


def test_default_mobile_policy_hides_economic_routes_from_every_entry_surface():
    policy = DEFAULT_MOBILE_FEATURE_POLICY
    assert policy.filter_manifest(("message.send", "wallet.transfer", "pho.balance", "task.create")) == (
        "message.send", "task.create",
    )
    for route in ("/api/wallet/dev/transfer", "/api/photon/invoice", "/api/mesh/local_send"):
        with pytest.raises(PermissionError, match="Dormant economic route"):
            policy.require_allowed(route=route)
    with pytest.raises(PermissionError, match="Dormant economic request"):
        policy.require_allowed(request="Pilot transfer 10 PHO")


def test_shared_fixture_supports_three_isolated_modes():
    fixture_path = Path("docs/aion/fixtures/pilot_unified_mobile_v1.json")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert fixture["schema_version"] == CONTRACT_VERSION
    memberships = {item["membership_id"]: Membership(**{**item, "scopes": tuple(item["scopes"])}) for item in fixture["memberships"]}
    leases = {item["lease_id"]: CapabilityLease(**{**item, "scopes": tuple(item["scopes"])}) for item in fixture["leases"]}
    manifests = {item["mode"]: item for item in fixture["surface_manifests"]}
    assert set(manifests) == {"personal", "workspace", "boardroom"}
    assert "Finance" not in manifests["workspace"]["shortcuts"]
    assert "Finance" in manifests["boardroom"]["shortcuts"]
    assert "Calendar" in manifests["personal"]["shortcuts"]
    for membership in memberships.values():
        lease = next(item for item in leases.values() if item.membership_id == membership.membership_id)
        assert lease.persona_id == membership.persona_id
        assert lease.space_id == membership.space_id
        assert set(lease.scopes) <= set(membership.scopes)
