from __future__ import annotations

from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.live_context import LiveContextStore
from backend.modules.aion_fabric.moments import PilotMomentStore


def test_live_context_persists_only_structured_evidence(tmp_path):
    store = LiveContextStore(tmp_path)
    record = store.build(
        device_state={"foreground_app_id": "youtube.leanback.v4", "foreground_app_title": "YouTube", "volume": 18},
        recent_transcripts=["The claim says inflation fell to two percent"],
        belief={"surface": "youtube"},
    )
    assert record["recent_statement"] == "The claim says inflation fell to two percent"
    assert record["privacy"]["raw_audio_retained"] is False
    persisted = store.path.read_text(encoding="utf-8").lower()
    assert "audio_samples" not in persisted
    assert "audio_bytes" not in persisted
    assert store.latest()["context_hash"] == record["context_hash"]


def test_pilot_moment_is_signed_and_never_claims_to_copy_protected_media(tmp_path):
    identity = IdentityStore(tmp_path / "identity").load_or_create()
    context = LiveContextStore(tmp_path).build(
        device_state={"foreground_app_id": "netflix", "foreground_app_title": "Netflix"},
        recent_transcripts=["That was brilliant"],
    )
    moment = PilotMomentStore(tmp_path).create(
        context=context,
        request="Pilot share that",
        issuer_node_id="node_test",
        public_key=identity.public_key_b64,
        signer=identity.sign,
        recipient="Mike",
    )
    assert moment["delivery_state"] == "prepared_not_sent"
    assert moment["rights"]["protected_audio_copied"] is False
    assert moment["rights"]["protected_video_copied"] is False
    assert moment["share_mode"] == "context_card"
    assert moment["signature"]


def test_fact_check_moment_requires_private_recipient_and_separate_send(tmp_path):
    identity = IdentityStore(tmp_path / "identity").load_or_create()
    store = PilotMomentStore(tmp_path)
    moment = store.create_fact_check(
        fact_check={
            "fact_check_id": "fact_test",
            "evidence_hash": "a" * 64,
            "statement": "A current test claim",
            "verdict": "Misleading",
            "confidence": 0.8,
            "summary": "Important context was omitted.",
            "sources": [{"title": "Official evidence", "url": "https://example.gov/evidence"}],
        },
        request="Pilot send this fact-check",
        issuer_node_id="node_test",
        public_key=identity.public_key_b64,
        signer=identity.sign,
    )
    assert moment["delivery_state"] == "prepared_not_sent"
    assert moment["recipient"] is None

    preview = store.set_recipient(
        moment["moment_id"], persona_id="persona_owner", route="email", recipient="friend@example.com"
    )
    assert preview["delivery_state"] == "awaiting_send_confirmation"
    assert preview["preview_hash"]

    pending = store.send(
        moment["moment_id"], persona_id="persona_owner", preview_hash=preview["preview_hash"]
    )
    assert pending["delivery_state"] == "approved_pending_adapter"
    assert pending["delivery"]["receipt"] is None

    store.register_delivery_adapter(
        "email", lambda record: {"verified": True, "provider_reference": "message_test"}
    )
    delivered = store.send(
        moment["moment_id"], persona_id="persona_owner", preview_hash=preview["preview_hash"]
    )
    assert delivered["delivery_state"] == "delivered"


def test_fact_check_moment_can_be_delivered_to_authorized_local_private_phone(tmp_path):
    identity = IdentityStore(tmp_path / "identity").load_or_create()
    store = PilotMomentStore(tmp_path)
    moment = store.create_fact_check(
        fact_check={
            "fact_check_id": "fact_1",
            "evidence_hash": "evidence_hash",
            "statement": "Example claim",
            "verdict": "Supported",
            "summary": "Verified against public evidence.",
            "sources": [{"title": "Public source", "url": "https://example.org/evidence"}],
        },
        request="send this fact check to my phone",
        issuer_node_id="node_mother",
        public_key=identity.public_key_b64,
        signer=identity.sign,
    )
    preview = store.set_recipient(moment["moment_id"], persona_id="persona_owner", route="private_phone", recipient="")
    delivered = store.send(moment["moment_id"], persona_id="persona_owner", preview_hash=preview["preview_hash"])

    assert delivered["delivery_state"] == "delivered"
    assert delivered["delivery"]["receipt"]["verified"] is True
    assert store.snapshot()["private_phone_inbox"][0]["fact_check"]["fact_check_id"] == "fact_1"
    assert delivered["delivery"]["receipt"]["verified"] is True


def test_moment_rejects_replay_and_supports_revoke_and_delete(tmp_path):
    identity = IdentityStore(tmp_path / "identity").load_or_create()
    store = PilotMomentStore(tmp_path)
    context = LiveContextStore(tmp_path).build(device_state={"foreground_app_id": "youtube"}, recent_transcripts=["test"])
    first = store.create(context=context, request="share", issuer_node_id="node", public_key=identity.public_key_b64, signer=identity.sign)
    preview = store.set_recipient(first["moment_id"], persona_id="owner", route="messaging", recipient="Trusted contact")
    try:
        store.send(first["moment_id"], persona_id="owner", preview_hash="wrong")
        assert False, "a changed preview must not send"
    except PermissionError:
        pass
    revoked = store.revoke(first["moment_id"], persona_id="owner")
    assert revoked["delivery_state"] == "revoked"

    second = store.create(context=context, request="share another", issuer_node_id="node", public_key=identity.public_key_b64, signer=identity.sign)
    deleted = store.delete(second["moment_id"], persona_id="owner")
    assert deleted["delivery_state"] == "deleted"
    assert deleted["recent_statement"] == ""


def test_legacy_moment_is_safely_upgraded_before_private_action(tmp_path):
    store = PilotMomentStore(tmp_path)
    legacy = {
        "schema_version": "pilot.moment.v1",
        "moment_id": "moment_legacy",
        "delivery_state": "prepared_not_sent",
        "payload_hash": "b" * 64,
    }
    store.path.write_text(__import__("json").dumps(legacy), encoding="utf-8")
    upgraded = store.set_recipient(
        "moment_legacy", persona_id="owner", route="messaging", recipient="Trusted contact"
    )
    assert upgraded["schema_version"] == "pilot.moment.v2"
    assert upgraded["expires_at"]
    assert upgraded["delivery"]["attempts"] == 0


def test_moment_abuse_report_blocks_delivery(tmp_path):
    identity = IdentityStore(tmp_path / "identity").load_or_create()
    store = PilotMomentStore(tmp_path)
    context = LiveContextStore(tmp_path).build(device_state={}, recent_transcripts=["context"])
    moment = store.create(context=context, request="share", issuer_node_id="node", public_key=identity.public_key_b64, signer=identity.sign)
    reported = store.report_abuse(moment["moment_id"], persona_id="recipient", reason="unwanted")
    assert reported["delivery_state"] == "reported_and_blocked"
    assert reported["abuse_report"]["reason"] == "unwanted"
