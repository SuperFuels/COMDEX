from __future__ import annotations

import copy
import base64
import json
import ssl
from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.local_tls import LocalTLSAuthority
from backend.modules.aion_fabric.pilot_inbox import PilotInbox
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.pilot_unified.inbox import UnifiedInbox
from backend.modules.pilot_unified.inbox_live_service import UnifiedInboxLiveService
from backend.modules.pilot_unified.pairing import MobilePairingAuthority
from backend.modules.pilot_unified.proof_rail import SelectiveProofRail
from websockets.exceptions import ConnectionClosedError
from websockets.sync.client import connect


def _mother(root, name):
    identity = IdentityStore(root / "mother_identity").load_or_create()
    identities = ProductionPrivateIdentity(root)
    profile = identities.onboard(display_name=name)
    pairing = MobilePairingAuthority(
        root,
        mother_id=f"mother_{name.lower()}",
        mother_identity=identity,
        endpoint=f"https://{name.lower()}.pilot.test:8770",
        ca_sha256="ab" * 32,
        identity_registry=identities,
    )
    pilot_inbox = PilotInbox(root, identities=identities)
    inbox = UnifiedInbox(
        root,
        mother_id=f"mother_{name.lower()}",
        mother_identity=identity,
        pairing_authority=pairing,
        pilot_inbox=pilot_inbox,
    )
    phone = IdentityStore(root / "phone_identity").load_or_create()
    challenge = pairing.begin_pairing(
        persona_id=profile["persona_id"],
        device_label=f"{name} phone",
        phone_public_key=phone.public_key_b64,
        requested_scopes=("inbox.read", "message.send", "task.create", "task.respond"),
    )
    signed = {
        key: challenge["phone_challenge"][key]
        for key in (
            "schema_version", "challenge_id", "mother_id", "mother_fingerprint",
            "mother_descriptor_hash", "persona_id", "device_id", "device_label",
            "requested_scopes", "nonce", "issued_at", "expires_at",
        )
    }
    paired = pairing.complete_pairing(
        challenge_id=signed["challenge_id"],
        confirmation_code=challenge["local_confirmation"]["confirmation_code"],
        phone_signature=phone.sign(canonical_bytes(signed)),
    )
    return {
        "identity": identity,
        "identities": identities,
        "profile": profile,
        "pairing": pairing,
        "pilot_inbox": pilot_inbox,
        "inbox": inbox,
        "phone": phone,
        "certificate": paired["certificate"],
        "lease": paired["lease"],
    }


def _signed(phone, request):
    return phone.sign(canonical_bytes(request))


def _live_request(mother, *, after_revision=0):
    request = {
        "purpose": "open_inbox_stream",
        "persona_id": mother["profile"]["persona_id"],
        "device_id": mother["certificate"]["device_id"],
        "lease_id": mother["lease"]["lease_id"],
        "nonce": f"live_nonce_{after_revision}_long_enough",
        "after_revision": after_revision,
    }
    return {
        "request": request,
        "certificate": mother["certificate"],
        "lease": mother["lease"],
        "phone_signature": _signed(mother["phone"], request),
    }


def _prepare_and_send(alice, bob, *, request_key="alice_task_1"):
    alice["inbox"].trust_peer(bob["inbox"].descriptor())
    bob["inbox"].trust_peer(alice["inbox"].descriptor())
    alice["pilot_inbox"].save_contact(
        owner_persona_id=alice["profile"]["persona_id"],
        display_name="Bob",
        pilot_persona_id=bob["profile"]["persona_id"],
        pilot_mother_id=bob["inbox"].mother_id,
        preferred_route="pilot",
    )
    resolved = alice["inbox"].resolve_pilot_contact(
        persona_id=alice["profile"]["persona_id"],
        display_name="Bob",
        certificate=alice["certificate"],
        lease=alice["lease"],
    )
    request = {
        "persona_id": alice["profile"]["persona_id"],
        "recipient_persona_id": resolved["recipient_persona_id"],
        "recipient_mother_id": resolved["recipient_mother_id"],
        "title": "Collect the dry cleaning",
        "idempotency_key": request_key,
    }
    proposal = alice["inbox"].prepare_task(
        request,
        certificate=alice["certificate"],
        lease=alice["lease"],
        phone_signature=_signed(alice["phone"], request),
    )
    approval = {
        "persona_id": alice["profile"]["persona_id"],
        "action_id": proposal["action_id"],
        "scope_hash": proposal["scope_hash"],
        "decision": "approved",
        "idempotency_key": f"approve_{request_key}",
    }
    packet = alice["inbox"].approve_and_export_task(
        approval,
        certificate=alice["certificate"],
        lease=alice["lease"],
        phone_signature=_signed(alice["phone"], approval),
    )
    return proposal, packet


def test_two_mothers_deliver_accept_and_reconcile_one_encrypted_task(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    proposal, packet = _prepare_and_send(alice, bob)

    stored = (tmp_path / "alice" / "pilot_unified_inbox" / "state.json").read_text()
    assert "Collect the dry cleaning" not in stored
    assert "Collect the dry cleaning" not in str(packet)

    received = bob["inbox"].receive_packet(packet)
    assert received["status"] == "awaiting_recipient_acceptance"
    assert received["title"] == "Collect the dry cleaning"
    local_before = bob["pilot_inbox"].stream(persona_id=bob["profile"]["persona_id"])
    assert local_before["unaccepted_tasks"] == 1

    response = {
        "persona_id": bob["profile"]["persona_id"],
        "action_id": proposal["action_id"],
        "decision": "accepted",
        "idempotency_key": "bob_accept_1",
    }
    receipt = bob["inbox"].respond_to_task(
        response,
        certificate=bob["certificate"],
        lease=bob["lease"],
        phone_signature=_signed(bob["phone"], response),
    )
    reconciled = alice["inbox"].reconcile_receipt(receipt)
    assert reconciled["status"] == "accepted"
    assert bob["pilot_inbox"].stream(persona_id=bob["profile"]["persona_id"])["tasks"][0]["status"] == "open"
    assert receipt["private_content_included"] is False


def test_structured_task_emits_authorization_delivery_and_acceptance_proofs(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    alice["inbox"].proof_rail = SelectiveProofRail(
        tmp_path / "alice", mother_identity=alice["identity"]
    )
    bob["inbox"].proof_rail = SelectiveProofRail(
        tmp_path / "bob", mother_identity=bob["identity"]
    )
    proposal, packet = _prepare_and_send(alice, bob, request_key="proof_task_1")
    bob["inbox"].receive_packet(packet)
    response = {
        "persona_id": bob["profile"]["persona_id"],
        "action_id": proposal["action_id"],
        "decision": "accepted",
        "idempotency_key": "proof_accept_1",
    }
    bob["inbox"].respond_to_task(
        response,
        certificate=bob["certificate"],
        lease=bob["lease"],
        phone_signature=_signed(bob["phone"], response),
    )

    alice_state = json.loads(alice["inbox"].proof_rail.path.read_text(encoding="utf-8"))
    bob_state = json.loads(bob["inbox"].proof_rail.path.read_text(encoding="utf-8"))
    assert [item["event"] for item in alice_state["commitments"]] == ["authorization", "delivery"]
    assert [item["event"] for item in bob_state["commitments"]] == ["acceptance"]
    rendered = json.dumps({"alice": alice_state, "bob": bob_state})
    assert "Collect the dry cleaning" not in rendered


def test_live_inbox_uses_signed_phone_possession_and_resume_cursor(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    alice["inbox"].trust_peer(alice["inbox"].descriptor())
    tls = LocalTLSAuthority(tmp_path / "tls").ensure(address="127.0.0.1", hostname="pilot-live.test")
    service = UnifiedInboxLiveService(
        alice["inbox"], tls_context=tls.context(), address="127.0.0.1", port=0,
        allowed_origins=("https://app.pilot.test",),
    )
    service.start()
    context = ssl.create_default_context(cafile=str(tls.ca_certificate_path))
    try:
        with connect(service.public_url, ssl=context, origin="https://app.pilot.test", open_timeout=3) as socket:
            socket.send(json.dumps(_live_request(alice)))
            ready = json.loads(socket.recv(timeout=3))
            snapshot = json.loads(socket.recv(timeout=3))
            assert ready["type"] == "inbox.ready"
            assert ready["resumed_from_revision"] == 0
            assert ready["duplicates_replayed"] == 0
            assert snapshot["type"] == "inbox.snapshot"
            revision = snapshot["stream"]["revision"]

        with connect(service.public_url, ssl=context, origin="https://app.pilot.test", open_timeout=3) as socket:
            socket.send(json.dumps(_live_request(alice, after_revision=revision)))
            ready = json.loads(socket.recv(timeout=3))
            assert ready["resumed_from_revision"] == revision
            socket.send("ping")
            heartbeat = json.loads(socket.recv(timeout=3))
            assert heartbeat == {"type": "inbox.heartbeat", "revision": revision}
    finally:
        service.stop()


def test_live_inbox_rejects_unsigned_connection(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    tls = LocalTLSAuthority(tmp_path / "tls").ensure(address="127.0.0.1", hostname="pilot-live.test")
    service = UnifiedInboxLiveService(
        alice["inbox"], tls_context=tls.context(), address="127.0.0.1", port=0,
        allowed_origins=("https://app.pilot.test",),
    )
    service.start()
    context = ssl.create_default_context(cafile=str(tls.ca_certificate_path))
    payload = _live_request(alice)
    payload["phone_signature"] = "invalid"
    try:
        with connect(service.public_url, ssl=context, origin="https://app.pilot.test", open_timeout=3) as socket:
            socket.send(json.dumps(payload))
            with pytest.raises(ConnectionClosedError) as closed:
                socket.recv(timeout=3)
            assert closed.value.rcvd.code == 1008
    finally:
        service.stop()


def test_task_lifecycle_reconciles_correction_read_snooze_completion_and_cancel(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    proposal, packet = _prepare_and_send(alice, bob)
    bob["inbox"].receive_packet(packet)

    correction = {
        "persona_id": alice["profile"]["persona_id"], "action_id": proposal["action_id"],
        "event": "corrected", "title": "Collect the dry cleaning before six",
        "idempotency_key": "alice_correct_1",
    }
    corrected = alice["inbox"].transition_task(
        correction, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], correction),
    )
    received_correction = bob["inbox"].receive_packet(corrected["delivery_packet"])
    assert received_correction["title"] == "Collect the dry cleaning before six"
    assert bob["inbox"].receive_packet(corrected["delivery_packet"])["title"] == received_correction["title"]

    read_request = {
        "persona_id": bob["profile"]["persona_id"], "action_id": proposal["action_id"],
        "event": "read", "idempotency_key": "bob_read_1",
    }
    read_receipt = bob["inbox"].transition_task(
        read_request, certificate=bob["certificate"], lease=bob["lease"],
        phone_signature=_signed(bob["phone"], read_request),
    )
    assert alice["inbox"].reconcile_receipt(read_receipt)["read_at"]

    accept = {
        "persona_id": bob["profile"]["persona_id"], "action_id": proposal["action_id"],
        "decision": "accepted", "idempotency_key": "bob_accept_lifecycle",
    }
    accepted_receipt = bob["inbox"].respond_to_task(
        accept, certificate=bob["certificate"], lease=bob["lease"],
        phone_signature=_signed(bob["phone"], accept),
    )
    alice["inbox"].reconcile_receipt(accepted_receipt)
    until = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    snooze = {
        "persona_id": bob["profile"]["persona_id"], "action_id": proposal["action_id"],
        "event": "snoozed", "until": until, "idempotency_key": "bob_snooze_1",
    }
    snooze_receipt = bob["inbox"].transition_task(
        snooze, certificate=bob["certificate"], lease=bob["lease"],
        phone_signature=_signed(bob["phone"], snooze),
    )
    assert alice["inbox"].reconcile_receipt(snooze_receipt)["snoozed_until"] == until
    complete = {
        "persona_id": bob["profile"]["persona_id"], "action_id": proposal["action_id"],
        "event": "completed", "idempotency_key": "bob_complete_1",
    }
    complete_receipt = bob["inbox"].transition_task(
        complete, certificate=bob["certificate"], lease=bob["lease"],
        phone_signature=_signed(bob["phone"], complete),
    )
    assert alice["inbox"].reconcile_receipt(complete_receipt)["status"] == "completed"

    second, second_packet = _prepare_and_send(alice, bob, request_key="alice_task_cancel")
    bob["inbox"].receive_packet(second_packet)
    cancel = {
        "persona_id": alice["profile"]["persona_id"], "action_id": second["action_id"],
        "event": "cancelled", "idempotency_key": "alice_cancel_1",
    }
    cancel_result = alice["inbox"].transition_task(
        cancel, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], cancel),
    )
    assert bob["inbox"].receive_packet(cancel_result["delivery_packet"])["status"] == "cancelled"


def test_task_failure_and_expiry_are_signed_and_fail_closed(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    first, packet = _prepare_and_send(alice, bob)
    bob["inbox"].receive_packet(packet)
    failed = {
        "persona_id": bob["profile"]["persona_id"], "action_id": first["action_id"],
        "event": "failed", "idempotency_key": "bob_failed_1",
    }
    receipt = bob["inbox"].transition_task(
        failed, certificate=bob["certificate"], lease=bob["lease"],
        phone_signature=_signed(bob["phone"], failed),
    )
    assert alice["inbox"].reconcile_receipt(receipt)["status"] == "failed"
    altered = copy.deepcopy(receipt)
    altered["state"] = "completed"
    with pytest.raises(PermissionError, match="verify"):
        alice["inbox"].reconcile_receipt(altered)

    second, second_packet = _prepare_and_send(alice, bob, request_key="alice_task_expire")
    bob["inbox"].receive_packet(second_packet)
    state = bob["inbox"]._read()
    expiring = next(item for item in state["actions"] if item["action_id"] == second["action_id"])
    expiring["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    bob["inbox"]._write(state)
    expired = {
        "persona_id": bob["profile"]["persona_id"], "action_id": second["action_id"],
        "event": "expired", "idempotency_key": "bob_expired_1",
    }
    expired_receipt = bob["inbox"].transition_task(
        expired, certificate=bob["certificate"], lease=bob["lease"],
        phone_signature=_signed(bob["phone"], expired),
    )
    assert alice["inbox"].reconcile_receipt(expired_receipt)["status"] == "expired"


def test_idempotent_prepare_and_delivery_replay_do_not_duplicate(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    first, packet = _prepare_and_send(alice, bob)
    request = {
        "persona_id": alice["profile"]["persona_id"],
        "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id,
        "title": "Collect the dry cleaning",
        "idempotency_key": "alice_task_1",
    }
    repeated = alice["inbox"].prepare_task(
        request,
        certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], request),
    )
    assert repeated["action_id"] == first["action_id"]
    one = bob["inbox"].receive_packet(packet)
    two = bob["inbox"].receive_packet(packet)
    assert one["action_id"] == two["action_id"]
    assert len(bob["pilot_inbox"].stream(persona_id=bob["profile"]["persona_id"])["tasks"]) == 1

    changed = {**request, "title": "A different task"}
    with pytest.raises(PermissionError, match="different content"):
        alice["inbox"].prepare_task(
            changed,
            certificate=alice["certificate"], lease=alice["lease"],
            phone_signature=_signed(alice["phone"], changed),
        )


def test_packet_tampering_wrong_space_and_revoked_phone_fail_closed(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    _, packet = _prepare_and_send(alice, bob)
    tampered = copy.deepcopy(packet)
    tampered["recipient_persona_id"] = alice["profile"]["persona_id"]
    with pytest.raises(PermissionError, match="changed in transit"):
        bob["inbox"].receive_packet(tampered)

    alice["pairing"].revoke_device(device_id=alice["certificate"]["device_id"], reason="lost")
    request = {
        "persona_id": alice["profile"]["persona_id"],
        "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id,
        "title": "Unauthorized task",
        "idempotency_key": "revoked_attempt",
    }
    with pytest.raises(PermissionError, match="no longer trusted"):
        alice["inbox"].prepare_task(
            request,
            certificate=alice["certificate"], lease=alice["lease"],
            phone_signature=_signed(alice["phone"], request),
        )


def test_persona_streams_cannot_read_another_identity(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    other = alice["identities"].onboard(display_name="Other")
    with pytest.raises(PermissionError, match="another person's"):
        alice["inbox"].stream(
            persona_id=other["persona_id"],
            certificate=alice["certificate"],
            lease=alice["lease"],
        )


def test_text_message_is_encrypted_deduplicated_and_delivered(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    alice["inbox"].trust_peer(bob["inbox"].descriptor())
    bob["inbox"].trust_peer(alice["inbox"].descriptor())
    request = {
        "persona_id": alice["profile"]["persona_id"],
        "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id,
        "body": "Can you collect this on the way home?",
        "idempotency_key": "message_alice_1",
    }
    sent = alice["inbox"].send_text(
        request,
        certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], request),
    )
    repeated = alice["inbox"].send_text(
        request,
        certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], request),
    )
    assert repeated["message_id"] == sent["message_id"]
    assert "Can you collect" not in (tmp_path / "alice" / "pilot_unified_inbox" / "state.json").read_text()
    assert "Can you collect" not in str(sent["delivery_packet"])
    delivered = bob["inbox"].receive_packet(sent["delivery_packet"])
    assert delivered["body"] == request["body"]
    assert delivered["status"] == "delivered"
    stream = bob["inbox"].stream(
        persona_id=bob["profile"]["persona_id"],
        certificate=bob["certificate"], lease=bob["lease"],
    )
    assert stream["messages"][0]["message_id"] == sent["message_id"]


def test_attachment_is_encrypted_transferred_verified_and_read_by_recipient(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    alice["inbox"].trust_peer(bob["inbox"].descriptor())
    bob["inbox"].trust_peer(alice["inbox"].descriptor())
    raw = b"Private proposal contents\nLine two\n"
    request = {
        "persona_id": alice["profile"]["persona_id"],
        "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id,
        "filename": "proposal.txt", "media_type": "text/plain",
        "content_base64": base64.b64encode(raw).decode("ascii"),
        "idempotency_key": "attachment_alice_1",
    }
    sent = alice["inbox"].send_attachment(
        request, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], request),
    )
    assert raw.decode() not in (tmp_path / "alice" / "pilot_unified_inbox" / "state.json").read_text()
    assert raw.decode() not in str(sent["delivery_packet"])
    delivered = bob["inbox"].receive_packet(sent["delivery_packet"])
    attachment = delivered["attachments"][0]
    assert attachment["filename"] == "proposal.txt"
    assert attachment["encrypted"] is True
    blob = next((tmp_path / "bob" / "pilot_unified_inbox").glob("attachment_*.blob"))
    assert raw not in blob.read_bytes()
    read = {
        "persona_id": bob["profile"]["persona_id"],
        "attachment_id": attachment["attachment_id"],
        "idempotency_key": "read_attachment_bob_1",
    }
    opened = bob["inbox"].read_attachment(
        read, certificate=bob["certificate"], lease=bob["lease"],
        phone_signature=_signed(bob["phone"], read),
    )
    assert base64.b64decode(opened["content_base64"]) == raw
    encrypted = bytearray(blob.read_bytes())
    encrypted[-1] ^= 1
    blob.write_bytes(encrypted)
    with pytest.raises(RuntimeError, match="integrity"):
        bob["inbox"].read_attachment(
            {**read, "idempotency_key": "read_attachment_bob_2"},
            certificate=bob["certificate"], lease=bob["lease"],
            phone_signature=_signed(bob["phone"], {**read, "idempotency_key": "read_attachment_bob_2"}),
        )


def test_attachment_limits_tampering_and_unrelated_person_fail_closed(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    alice["inbox"].trust_peer(bob["inbox"].descriptor())
    bob["inbox"].trust_peer(alice["inbox"].descriptor())
    request = {
        "persona_id": alice["profile"]["persona_id"],
        "recipient_persona_id": bob["profile"]["persona_id"], "recipient_mother_id": bob["inbox"].mother_id,
        "filename": "note.txt", "media_type": "text/plain",
        "content_base64": base64.b64encode(b"hello").decode("ascii"),
        "idempotency_key": "attachment_tamper_1",
    }
    sent = alice["inbox"].send_attachment(
        request, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], request),
    )
    tampered = copy.deepcopy(sent["delivery_packet"])
    tampered["ciphertext"] = tampered["ciphertext"][:-2] + "AA"
    with pytest.raises(PermissionError, match="changed in transit"):
        bob["inbox"].receive_packet(tampered)
    bad_type = {**request, "media_type": "application/x-executable", "idempotency_key": "attachment_bad_type"}
    with pytest.raises(ValueError, match="supported attachment"):
        alice["inbox"].send_attachment(
            bad_type, certificate=alice["certificate"], lease=alice["lease"],
            phone_signature=_signed(alice["phone"], bad_type),
        )
    wrong_person = {
        "persona_id": alice["profile"]["persona_id"], "attachment_id": sent["attachments"][0]["attachment_id"],
        "idempotency_key": "wrong_person_read",
    }
    with pytest.raises(PermissionError, match="identity"):
        bob["inbox"].read_attachment(
            wrong_person, certificate=bob["certificate"], lease=bob["lease"],
            phone_signature=_signed(bob["phone"], wrong_person),
        )


def test_unified_search_filters_messages_tasks_and_files_after_authorization(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    proposal, packet = _prepare_and_send(alice, bob)
    bob["inbox"].receive_packet(packet)
    text_request = {
        "persona_id": alice["profile"]["persona_id"], "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id, "body": "The ladder shortlist is ready",
        "idempotency_key": "search_message_1",
    }
    text_message = alice["inbox"].send_text(
        text_request, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], text_request),
    )
    bob["inbox"].receive_packet(text_message["delivery_packet"])
    attachment_request = {
        "persona_id": alice["profile"]["persona_id"], "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id, "filename": "ladder-comparison.pdf",
        "media_type": "application/pdf", "content_base64": base64.b64encode(b"%PDF-safe-test").decode("ascii"),
        "idempotency_key": "search_file_1",
    }
    attachment_message = alice["inbox"].send_attachment(
        attachment_request, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], attachment_request),
    )
    bob["inbox"].receive_packet(attachment_message["delivery_packet"])

    def search(query, kind, key):
        request = {"persona_id": bob["profile"]["persona_id"], "query": query, "kind": kind, "idempotency_key": key}
        return bob["inbox"].search(
            request, certificate=bob["certificate"], lease=bob["lease"],
            phone_signature=_signed(bob["phone"], request),
        )

    assert [item["result_type"] for item in search("ladder", "all", "search_all")["results"]] == ["file", "message"]
    assert search("dry cleaning", "tasks", "search_tasks")["results"][0]["action_id"] == proposal["action_id"]
    assert search("ladder", "files", "search_files")["results"][0]["attachments"][0]["filename"] == "ladder-comparison.pdf"
    assert search("ladder", "messages", "search_messages")["results"][0]["body"] == "The ladder shortlist is ready"


def test_voice_note_is_bounded_encrypted_retained_and_delivered(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    alice["inbox"].trust_peer(bob["inbox"].descriptor())
    bob["inbox"].trust_peer(alice["inbox"].descriptor())
    audio = b"webm-test-audio-bytes" * 20
    request = {
        "persona_id": alice["profile"]["persona_id"], "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id, "media_type": "audio/webm",
        "content_base64": base64.b64encode(audio).decode("ascii"), "duration_ms": 1_400,
        "retention_seconds": 300, "idempotency_key": "voice_note_alice_1",
    }
    sent = alice["inbox"].send_voice_note(
        request, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], request),
    )
    assert sent["kind"] == "voice_note"
    assert audio not in next((tmp_path / "alice" / "pilot_unified_inbox").glob("attachment_*.blob")).read_bytes()
    delivered = bob["inbox"].receive_packet(sent["delivery_packet"])
    voice = delivered["attachments"][0]
    assert voice["duration_ms"] == 1_400
    read = {"persona_id": bob["profile"]["persona_id"], "attachment_id": voice["attachment_id"], "idempotency_key": "voice_read_1"}
    opened = bob["inbox"].read_attachment(
        read, certificate=bob["certificate"], lease=bob["lease"], phone_signature=_signed(bob["phone"], read),
    )
    assert base64.b64decode(opened["content_base64"]) == audio
    too_long = {**request, "duration_ms": 120_001, "idempotency_key": "voice_too_long"}
    with pytest.raises(ValueError, match="outside the supported bound"):
        alice["inbox"].send_voice_note(
            too_long, certificate=alice["certificate"], lease=alice["lease"],
            phone_signature=_signed(alice["phone"], too_long),
        )


def test_ptt_floor_is_bound_to_person_device_lease_and_expires(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    alice["inbox"].trust_peer(bob["inbox"].descriptor())
    request = {
        "persona_id": alice["profile"]["persona_id"], "operation": "acquire",
        "recipient_persona_id": bob["profile"]["persona_id"], "recipient_mother_id": bob["inbox"].mother_id,
        "idempotency_key": "ptt_acquire_1",
    }
    floor = alice["inbox"].control_ptt_floor(
        request, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], request),
    )
    repeated = alice["inbox"].control_ptt_floor(
        request, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], request),
    )
    assert repeated["floor_id"] == floor["floor_id"]

    second_phone = IdentityStore(tmp_path / "alice" / "second_phone").load_or_create()
    challenge = alice["pairing"].begin_pairing(
        persona_id=alice["profile"]["persona_id"], device_label="Alice second phone",
        phone_public_key=second_phone.public_key_b64, requested_scopes=("message.send",),
    )
    signed = {key: challenge["phone_challenge"][key] for key in (
        "schema_version", "challenge_id", "mother_id", "mother_fingerprint", "mother_descriptor_hash",
        "persona_id", "device_id", "device_label", "requested_scopes", "nonce", "issued_at", "expires_at",
    )}
    second = alice["pairing"].complete_pairing(
        challenge_id=signed["challenge_id"], confirmation_code=challenge["local_confirmation"]["confirmation_code"],
        phone_signature=second_phone.sign(canonical_bytes(signed)),
    )
    conflicting = {**request, "idempotency_key": "ptt_acquire_second_phone"}
    with pytest.raises(PermissionError, match="Someone else"):
        alice["inbox"].control_ptt_floor(
            conflicting, certificate=second["certificate"], lease=second["lease"],
            phone_signature=_signed(second_phone, conflicting),
        )
    stolen_release = {
        "persona_id": alice["profile"]["persona_id"], "operation": "release", "floor_id": floor["floor_id"],
        "idempotency_key": "ptt_stolen_release",
    }
    with pytest.raises(PermissionError, match="does not own"):
        alice["inbox"].control_ptt_floor(
            stolen_release, certificate=second["certificate"], lease=second["lease"],
            phone_signature=_signed(second_phone, stolen_release),
        )

    voice = {
        "persona_id": alice["profile"]["persona_id"], "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id, "media_type": "audio/webm",
        "content_base64": base64.b64encode(b"ptt-audio").decode("ascii"), "duration_ms": 600,
        "retention_seconds": 300, "ptt_floor_id": floor["floor_id"], "idempotency_key": "ptt_voice_send",
    }
    sent = alice["inbox"].send_voice_note(
        voice, certificate=alice["certificate"], lease=alice["lease"], phone_signature=_signed(alice["phone"], voice),
    )
    assert sent["kind"] == "voice_note"
    state = alice["inbox"]._read()
    assert next(item for item in state["ptt_floors"] if item["floor_id"] == floor["floor_id"])["status"] == "released"

    expiring = {**request, "idempotency_key": "ptt_acquire_expiring"}
    expiring_floor = alice["inbox"].control_ptt_floor(
        expiring, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=_signed(alice["phone"], expiring),
    )
    state = alice["inbox"]._read()
    stored_floor = next(item for item in state["ptt_floors"] if item["floor_id"] == expiring_floor["floor_id"])
    stored_floor["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    alice["inbox"]._write(state)
    after_expiry = {**request, "idempotency_key": "ptt_acquire_after_expiry"}
    replacement = alice["inbox"].control_ptt_floor(
        after_expiry, certificate=second["certificate"], lease=second["lease"],
        phone_signature=_signed(second_phone, after_expiry),
    )
    assert replacement["floor_id"] != expiring_floor["floor_id"]
    state = alice["inbox"]._read()
    assert next(item for item in state["ptt_floors"] if item["floor_id"] == expiring_floor["floor_id"])["status"] == "expired"


def test_structured_cards_cross_mothers_and_preserve_exact_private_scope(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    alice["inbox"].trust_peer(bob["inbox"].descriptor())
    bob["inbox"].trust_peer(alice["inbox"].descriptor())
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    later = (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
    cases = [
        ("reminder", {"due_at": future}),
        ("follow_up", {"due_at": future}),
        ("calendar", {"starts_at": future, "ends_at": later}),
        ("document_review", {}),
    ]
    for index, (card_type, schedule) in enumerate(cases):
        request = {
            "persona_id": alice["profile"]["persona_id"], "recipient_persona_id": bob["profile"]["persona_id"],
            "recipient_mother_id": bob["inbox"].mother_id, "card_type": card_type,
            "title": f"Review {card_type}", "detail": "Private exact detail", **schedule,
            "idempotency_key": f"card_{index}",
        }
        sent = alice["inbox"].send_structured_card(
            request, certificate=alice["certificate"], lease=alice["lease"],
            phone_signature=_signed(alice["phone"], request),
        )
        assert "Private exact detail" not in str(sent["delivery_packet"])
        delivered = bob["inbox"].receive_packet(sent["delivery_packet"])
        assert delivered["kind"] == card_type
        assert delivered["card"]["title"] == f"Review {card_type}"
        assert delivered["card"]["state"] == "proposed"
    query = {"persona_id": bob["profile"]["persona_id"], "query": "document", "kind": "all", "idempotency_key": "card_search"}
    result = bob["inbox"].search(
        query, certificate=bob["certificate"], lease=bob["lease"], phone_signature=_signed(bob["phone"], query),
    )
    assert result["results"][0]["card"]["card_type"] == "document_review"

    invalid = {
        "persona_id": alice["profile"]["persona_id"], "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id, "card_type": "calendar", "title": "Missing end",
        "starts_at": future, "idempotency_key": "bad_calendar_card",
    }
    with pytest.raises(ValueError, match="start and end"):
        alice["inbox"].send_structured_card(
            invalid, certificate=alice["certificate"], lease=alice["lease"],
            phone_signature=_signed(alice["phone"], invalid),
        )
