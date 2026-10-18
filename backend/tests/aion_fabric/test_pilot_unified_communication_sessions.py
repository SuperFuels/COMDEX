from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.pilot_unified.communication_sessions import CommunicationSessionAuthority


def _identity():
    return DeviceIdentity(Ed25519PrivateKey.generate())


def _transition(authority, call_id, actor, identity, target, nonce_suffix=""):
    payload = {"actor_persona_id": actor, "target_state": target, "nonce": f"nonce-{target}{nonce_suffix}"}
    return authority.transition_call(call_id=call_id, payload=payload, signature=identity.sign(canonical_bytes(payload)))


def _register_participant(authority, call_id, actor, identity):
    payload = {"purpose": "register_call_participant", "call_id": call_id, "actor_persona_id": actor, "nonce": f"register-{actor}"}
    authority.register_participant_key(
        call_id=call_id, persona_id=actor, public_key=identity.public_key_b64,
        proof_payload=payload, signature=identity.sign(canonical_bytes(payload)),
    )


def _transport(authority, call_id, actor, identity, epoch, byte):
    payload = {
        "purpose": "register_webrtc_transport", "call_id": call_id,
        "actor_persona_id": actor, "epoch": epoch,
        "transport_public_key": base64.b64encode(bytes([byte]) * 32).decode(),
        "dtls_fingerprint": ":".join([f"{byte:02X}"] * 32),
        "nonce": f"transport-{actor}-{epoch}",
    }
    return authority.register_webrtc_transport(
        call_id=call_id, payload=payload, signature=identity.sign(canonical_bytes(payload)),
    )


def _group_message(authority, group_id, actor, identity, epoch, body, *, reply_to=None, mentions=None, attachment=None, nonce="message-one"):
    payload = {
        "purpose": "post_group_message", "group_id": group_id,
        "actor_persona_id": actor, "body_hash": canonical_hash({"body": body}),
        "reply_to": reply_to, "mentions": list(mentions or []), "attachment": attachment,
        "key_epoch": epoch, "nonce": nonce,
    }
    return authority.add_group_message(payload=payload, signature=identity.sign(canonical_bytes(payload)))


def test_authenticated_call_lifecycle_and_key_rotation(tmp_path):
    authority = CommunicationSessionAuthority(tmp_path)
    alice, bob = _identity(), _identity()
    call = authority.create_call(caller_persona_id="alice", caller_public_key=alice.public_key_b64, callee_persona_id="bob")
    _register_participant(authority, call["call_id"], "bob", bob)
    assert _transition(authority, call["call_id"], "bob", bob, "ringing")["state"] == "ringing"
    assert _transition(authority, call["call_id"], "bob", bob, "answered")["state"] == "answered"
    assert _transport(authority, call["call_id"], "alice", alice, 1, 1)["both_participants_ready"] is False
    ready = _transport(authority, call["call_id"], "bob", bob, 1, 2)
    assert ready["both_participants_ready"] is True
    assert ready["server_session_key_held"] is False
    connected = _transition(authority, call["call_id"], "alice", alice, "connected")
    assert connected["key_epoch"] == 1
    assert connected["transport_authenticated"] is True
    reconnecting = _transition(authority, call["call_id"], "bob", bob, "reconnecting")
    assert reconnecting["key_epoch"] == 1
    with pytest.raises(PermissionError, match="fresh WebRTC epoch"):
        _transition(authority, call["call_id"], "alice", alice, "connected", "-premature")
    _transport(authority, call["call_id"], "alice", alice, 2, 3)
    _transport(authority, call["call_id"], "bob", bob, 2, 4)
    reconnected = _transition(authority, call["call_id"], "alice", alice, "connected", "-2")
    assert reconnected["key_epoch"] == 2
    assert reconnected["media_audit_status"] == "not_independently_audited"
    assert _transition(authority, call["call_id"], "bob", bob, "ended")["state"] == "ended"


def test_invalid_call_actor_and_transition_fail_closed(tmp_path):
    authority = CommunicationSessionAuthority(tmp_path)
    alice, bob, attacker = _identity(), _identity(), _identity()
    call = authority.create_call(caller_persona_id="alice", caller_public_key=alice.public_key_b64, callee_persona_id="bob")
    _register_participant(authority, call["call_id"], "bob", bob)
    payload = {"actor_persona_id": "bob", "target_state": "ringing", "nonce": "x"}
    with pytest.raises(PermissionError):
        authority.transition_call(call_id=call["call_id"], payload=payload, signature=attacker.sign(canonical_bytes(payload)))
    with pytest.raises(PermissionError):
        _transition(authority, call["call_id"], "alice", alice, "answered")


def test_participant_and_transport_registration_require_signed_possession_and_reject_replay(tmp_path):
    authority = CommunicationSessionAuthority(tmp_path)
    alice, bob, attacker = _identity(), _identity(), _identity()
    call = authority.create_call(caller_persona_id="alice", caller_public_key=alice.public_key_b64, callee_persona_id="bob")
    proof = {"purpose": "register_call_participant", "call_id": call["call_id"], "actor_persona_id": "bob", "nonce": "register-bob"}
    with pytest.raises(PermissionError):
        authority.register_participant_key(
            call_id=call["call_id"], persona_id="bob", public_key=bob.public_key_b64,
            proof_payload=proof, signature=attacker.sign(canonical_bytes(proof)),
        )
    _register_participant(authority, call["call_id"], "bob", bob)
    first = _transport(authority, call["call_id"], "alice", alice, 1, 8)
    assert first["participant_authenticated"] is True
    with pytest.raises(PermissionError, match="replay"):
        _transport(authority, call["call_id"], "alice", alice, 1, 8)


def test_group_membership_roles_child_guardian_and_key_rotation(tmp_path):
    authority = CommunicationSessionAuthority(tmp_path)
    owner, member, child = _identity(), _identity(), _identity()
    group = authority.create_group(owner_persona_id="owner", name="Family", owner_public_key=owner.public_key_b64)
    added = authority.change_member(
        group_id=group["group_id"], actor_persona_id="owner", target_persona_id="member",
        operation="add", role="member", target_public_key=member.public_key_b64,
    )
    assert added["key_epoch"] == 2
    with pytest.raises(PermissionError, match="guardian"):
        authority.change_member(
            group_id=group["group_id"], actor_persona_id="owner", target_persona_id="child",
            operation="add", role="child", target_public_key=child.public_key_b64,
        )
    child_added = authority.change_member(
        group_id=group["group_id"], actor_persona_id="owner", target_persona_id="child",
        operation="add", role="child", target_public_key=child.public_key_b64, guardian_approved=True,
    )
    assert child_added["key_epoch"] == 3
    removed = authority.change_member(
        group_id=group["group_id"], actor_persona_id="owner", target_persona_id="member", operation="remove"
    )
    assert removed["key_epoch"] == 4
    assert next(item for item in removed["members"] if item["persona_id"] == "member")["status"] == "removed"


def test_group_reply_mentions_reactions_and_bounded_attachment(tmp_path):
    authority = CommunicationSessionAuthority(tmp_path)
    owner, member = _identity(), _identity()
    group = authority.create_group(owner_persona_id="owner", name="Project", owner_public_key=owner.public_key_b64)
    authority.change_member(
        group_id=group["group_id"], actor_persona_id="owner", target_persona_id="member",
        operation="add", role="member", target_public_key=member.public_key_b64,
    )
    first = _group_message(
        authority, group["group_id"], "owner", owner, 2, "hello",
        mentions=["member"], attachment={"attachment_id": "file_1", "byte_length": 42, "content_hash": "ab" * 32},
    )
    reply = _group_message(
        authority, group["group_id"], "member", member, 2, "reply",
        reply_to=first["message_id"], mentions=["owner"], nonce="message-two",
    )
    assert reply["reply_to"] == first["message_id"]
    reaction = authority.react(group_id=group["group_id"], message_id=first["message_id"], actor_persona_id="member", reaction="acknowledged")
    assert reaction["reactions"] == [{"persona_id": "member", "reaction": "acknowledged"}]
    with pytest.raises(ValueError):
        _group_message(
            authority, group["group_id"], "owner", owner, 2, "huge",
            attachment={"attachment_id": "huge", "byte_length": 1_000_001, "content_hash": "cd" * 32}, nonce="message-three",
        )


def test_adverse_network_loss_jitter_reconnect_and_compromised_device_fail_closed(tmp_path):
    authority = CommunicationSessionAuthority(tmp_path)
    alice, bob, attacker = _identity(), _identity(), _identity()
    call = authority.create_call(caller_persona_id="alice", caller_public_key=alice.public_key_b64, callee_persona_id="bob")
    _register_participant(authority, call["call_id"], "bob", bob)
    _transition(authority, call["call_id"], "bob", bob, "ringing", "-adverse")
    _transition(authority, call["call_id"], "bob", bob, "answered", "-adverse")
    # Jitter/reordering: Bob arrives first. Loss: Alice never arrives, so connect fails closed.
    _transport(authority, call["call_id"], "bob", bob, 1, 12)
    with pytest.raises(PermissionError, match="fresh WebRTC epoch"):
        _transition(authority, call["call_id"], "bob", bob, "connected", "-lost")
    # A forged transport cannot fill the missing participant slot.
    forged = {
        "purpose": "register_webrtc_transport", "call_id": call["call_id"],
        "actor_persona_id": "alice", "epoch": 1,
        "transport_public_key": base64.b64encode(bytes([13]) * 32).decode(),
        "dtls_fingerprint": ":".join(["0D"] * 32), "nonce": "forged-alice-one",
    }
    with pytest.raises(PermissionError):
        authority.register_webrtc_transport(call_id=call["call_id"], payload=forged, signature=attacker.sign(canonical_bytes(forged)))
    _transport(authority, call["call_id"], "alice", alice, 1, 13)
    _transition(authority, call["call_id"], "alice", alice, "connected", "-recovered")
    _transition(authority, call["call_id"], "bob", bob, "reconnecting", "-adverse")
    # Stale epoch packets arriving after reconnect are rejected.
    with pytest.raises(PermissionError, match="another call epoch"):
        _transport(authority, call["call_id"], "alice", alice, 1, 14)
    _transport(authority, call["call_id"], "bob", bob, 2, 15)
    _transport(authority, call["call_id"], "alice", alice, 2, 16)
    assert _transition(authority, call["call_id"], "bob", bob, "connected", "-fresh")["key_epoch"] == 2


def test_removed_group_participant_and_stolen_old_epoch_cannot_post(tmp_path):
    authority = CommunicationSessionAuthority(tmp_path)
    owner, member, attacker = _identity(), _identity(), _identity()
    group = authority.create_group(owner_persona_id="owner", name="Private", owner_public_key=owner.public_key_b64)
    authority.change_member(group_id=group["group_id"], actor_persona_id="owner", target_persona_id="member", operation="add", target_public_key=member.public_key_b64)
    _group_message(authority, group["group_id"], "member", member, 2, "before removal", nonce="before-remove")
    authority.change_member(group_id=group["group_id"], actor_persona_id="owner", target_persona_id="member", operation="remove")
    with pytest.raises(PermissionError, match="active group member"):
        _group_message(authority, group["group_id"], "member", member, 2, "after removal", nonce="after-remove")
    with pytest.raises(PermissionError):
        _group_message(authority, group["group_id"], "owner", attacker, 3, "forged", nonce="attacker-post")


def test_blocking_prevents_new_call(tmp_path):
    authority = CommunicationSessionAuthority(tmp_path)
    alice = _identity()
    authority.block(owner_persona_id="bob", blocked_persona_id="alice")
    with pytest.raises(PermissionError, match="blocked"):
        authority.create_call(caller_persona_id="alice", caller_public_key=alice.public_key_b64, callee_persona_id="bob")
    report = authority.report(
        reporter_persona_id="bob", reported_persona_id="alice", category="spam",
        evidence_hash=canonical_hash({"event": "unwanted-call"}),
    )
    assert report["provider_report_submitted"] is False
