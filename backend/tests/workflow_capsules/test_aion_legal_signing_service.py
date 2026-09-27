from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
from hashlib import sha256
import hmac
import io
import json
import zipfile

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.legal_signing_service import LegalSigningError, LegalSigningService
from backend.modules.aion_business.runtime.legal_document_proof import LegalDocumentProofService
from backend.modules.aion_business.runtime.legal_delivery_service import LegalDeliveryService
from backend.modules.chain_sim import chain_sim_model as chain_bank
from backend.modules.chain_sim.chain_sim_ledger import reset_ledger
from backend.modules.consensus.finality_certificate import build_finality_certificate, vote_sign_bytes


def test_envelope_requires_approval_and_returns_one_time_tokens(tmp_path):
    service = LegalSigningService(tmp_path)
    created = service.create_envelope(
        "home-fixed", title="Contractor agreement", document_content="Exact immutable terms",
        signers=[{"name": "Ada Lovelace", "email": "ada@example.com"}], actor_id="owner",
    )
    assert created["status"] == "DRAFT"
    with pytest.raises(LegalSigningError, match="invalid_envelope_state"):
        service.issue("home-fixed", created["envelope_id"], "owner")
    pending = service.submit_for_approval("home-fixed", created["envelope_id"], "owner")
    approved = service.approve("home-fixed", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("home-fixed", created["envelope_id"], "owner")
    assert approved["status"] == "APPROVED"
    assert issued["status"] == "ISSUED"
    assert len(issued["secure_links"][0]["token"]) > 30
    path = next((tmp_path / "home-fixed").glob("*.enc"))
    encrypted = path.read_text()
    assert issued["secure_links"][0]["token"] not in encrypted
    assert "Exact immutable terms" not in encrypted
    stored = service._read(path)
    assert stored["signers"][0]["token_hash"]


def test_identity_order_document_binding_and_signed_copy(tmp_path):
    service = LegalSigningService(tmp_path)
    created = service.create_envelope(
        "home-fixed", title="Terms", document_content="Version one",
        signers=[{"name": "First Signer", "email": "first@example.com"}, {"name": "Second Signer", "email": "second@example.com"}],
        actor_id="owner",
    )
    pending = service.submit_for_approval("home-fixed", created["envelope_id"], "owner")
    service.approve("home-fixed", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("home-fixed", created["envelope_id"], "owner")
    first, second = [item["token"] for item in issued["secure_links"]]
    with pytest.raises(LegalSigningError, match="signing_order_not_reached"):
        service.sign(second, "Second Signer", "second@example.com")
    with pytest.raises(LegalSigningError, match="identity"):
        service.sign(first, "Wrong Name", "first@example.com")
    progress = service.sign(first, "First Signer", "first@example.com")
    completed = service.sign(second, "Second Signer", "second@example.com")
    assert progress["status"] == "IN_PROGRESS"
    assert completed["status"] == "COMPLETED"
    assert completed["signed_copy"]["delivery_status"] == "READY_FOR_APPROVED_DELIVERY"
    assert completed["signers"][0]["accepted_document_hash"] == completed["document"]["content_hash"]
    assert service.verify_audit_chain("home-fixed", created["envelope_id"])
    with pytest.raises(LegalSigningError, match="secure_signing_link_invalid"):
        service.sign(first, "First Signer", "first@example.com")
    with pytest.raises(LegalSigningError, match="secure_signing_link_invalid"):
        service.decline(second, "replayed action")
    delivered = service.record_signed_copy_delivery("home-fixed", created["envelope_id"], "owner", completed["signers"][0]["signer_id"], "Gmail sent-message-123")
    assert delivered["delivery"]["signed_copy_delivery"][0]["manifest_hash"] == completed["signed_copy"]["manifest_hash"]
    assert service.verify_audit_chain("home-fixed", created["envelope_id"])


def test_completed_envelope_uses_approved_outbox_and_confirms_every_party(tmp_path):
    sent = []

    def sender(record):
        sent.append(record)
        return {
            "ok": True,
            "provider_request_id": f"provider-{record['signer_id']}",
            "provider_status": "accepted",
        }

    delivery = LegalDeliveryService(tmp_path, senders={"resend": sender})
    service = LegalSigningService(tmp_path, delivery_service=delivery)
    created = service.create_envelope(
        "w", title="Multi-party agreement", document_content="Exact shared terms",
        signers=[
            {"name": "First Signer", "email": "first@example.com"},
            {"name": "Second Signer", "email": "second@example.com"},
        ], actor_id="owner",
    )
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    service.sign(issued["secure_links"][0]["token"], "First Signer", "first@example.com")
    completed = service.sign(issued["secure_links"][1]["token"], "Second Signer", "second@example.com")

    queued = service.queue_signed_copy_deliveries(
        "w", created["envelope_id"], actor_id="owner", provider="resend",
        acknowledge_external_send=True,
    )
    assert queued["required_party_count"] == 2
    assert queued["counts"] == {"APPROVED_PENDING": 2}
    assert queued["all_required_parties_confirmed"] is False
    audit_count = len(service._load("w", created["envelope_id"])["audit_events"])
    repeated = service.queue_signed_copy_deliveries(
        "w", created["envelope_id"], actor_id="owner", provider="resend",
        acknowledge_external_send=True,
    )
    assert len(repeated["items"]) == 2
    assert len(service._load("w", created["envelope_id"])["audit_events"]) == audit_count

    submitted = service.send_queued_signed_copies(
        "w", actor_id="owner", acknowledge_external_send=True,
    )
    assert submitted["counts"] == {"SUBMITTED_TO_PROVIDER": 2}
    assert len(sent) == 2
    assert len({item["attachment"]["sha256"] for item in sent}) == 1
    assert all(item["manifest_hash"] == completed["signed_copy"]["manifest_hash"] for item in sent)

    for item in submitted["items"]:
        result = service.confirm_signed_copy_delivery(
            "w", item["delivery_id"], actor_id="provider_webhook",
            outcome="DELIVERED", provider_reference=f"delivered-{item['signer_id']}",
        )
    assert result["outbox"]["all_required_parties_confirmed"] is True
    envelope = service.get_envelope("w", created["envelope_id"])
    assert len(envelope["delivery"]["signed_copy_delivery"]) == 2
    assert service.verify_audit_chain("w", created["envelope_id"])


def test_authenticated_resend_callback_updates_envelope_delivery_record(tmp_path):
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    delivery = LegalDeliveryService(
        tmp_path, clock=lambda: now,
        senders={"resend": lambda _record: {
            "ok": True, "provider_request_id": "resend-email-123", "provider_status": "accepted",
        }},
    )
    service = LegalSigningService(tmp_path, clock=lambda: now, delivery_service=delivery)
    created = service.create_envelope(
        "w", title="Agreement", document_content="Exact terms",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
    )
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    service.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")
    service.queue_signed_copy_deliveries(
        "w", created["envelope_id"], actor_id="owner", provider="resend",
        acknowledge_external_send=True,
    )
    service.send_queued_signed_copies("w", actor_id="owner", acknowledge_external_send=True)

    raw = json.dumps({
        "type": "email.delivered", "created_at": "2026-09-26T12:00:00Z",
        "data": {"email_id": "resend-email-123", "to": ["a@example.com"]},
    }, separators=(",", ":")).encode("utf-8")
    secret = "whsec_" + base64.urlsafe_b64encode(b"r" * 32).decode("ascii")
    encoded = secret.removeprefix("whsec_")
    key = base64.urlsafe_b64decode(encoded + ("=" * (-len(encoded) % 4)))
    event_id = "msg-resend-delivered-123"
    timestamp = str(int(now.timestamp()))
    signature = base64.b64encode(hmac.new(
        key, f"{event_id}.{timestamp}.".encode("utf-8") + raw, sha256,
    ).digest()).decode("ascii")

    result = service.ingest_resend_delivery_webhook(
        raw,
        {"svix-id": event_id, "svix-timestamp": timestamp, "svix-signature": f"v1,{signature}"},
        webhook_secrets=secret,
    )
    assert result["outcome"] == "DELIVERED"
    envelope = service.get_envelope("w", created["envelope_id"])
    assert len(envelope["delivery"]["signed_copy_delivery"]) == 1
    assert envelope["delivery"]["signed_copy_delivery"][0]["delivery_reference"] == event_id
    assert service.verify_audit_chain("w", created["envelope_id"])


def test_microsoft_message_trace_updates_envelope_delivery_record(tmp_path):
    delivery = LegalDeliveryService(
        tmp_path,
        senders={"microsoft_graph": lambda _record: {
            "ok": True,
            "provider_request_id": "<legal-copy-1@example.onmicrosoft.com>",
            "provider_status": "submitted",
        }},
        receipt_checkers={"microsoft_graph": lambda record: {
            "ok": True,
            "found": True,
            "trace_id": "exchange-trace-legal-copy-1",
            "internet_message_id": record["provider_request_id"],
            "provider_status": "delivered",
            "observed_at": "2026-09-26T12:00:10Z",
        }},
    )
    service = LegalSigningService(tmp_path, delivery_service=delivery)
    created = service.create_envelope(
        "w", title="Agreement", document_content="Exact terms",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
    )
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    service.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")
    service.queue_signed_copy_deliveries(
        "w", created["envelope_id"], actor_id="owner", provider="microsoft_graph",
        acknowledge_external_send=True,
    )
    service.send_queued_signed_copies(
        "w", actor_id="owner", acknowledge_external_send=True,
    )

    result = service.refresh_microsoft_graph_delivery_receipts(
        "w", actor_id="owner", limit=10,
    )
    assert result["counts"] == {"DELIVERED": 1}
    envelope = service.get_envelope("w", created["envelope_id"])
    assert len(envelope["delivery"]["signed_copy_delivery"]) == 1
    assert envelope["delivery"]["signed_copy_delivery"][0]["delivery_reference"] == (
        "exchange-trace-legal-copy-1"
    )
    assert service.verify_audit_chain("w", created["envelope_id"])


def test_reminders_never_claim_external_delivery_without_connector(tmp_path):
    service = LegalSigningService(tmp_path)
    created = service.create_envelope("w", title="NDA", document_content="NDA terms", signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner")
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    reminded = service.record_reminder("w", created["envelope_id"], "owner", issued["signers"][0]["signer_id"])
    assert reminded["delivery"]["external_delivery_enabled"] is False
    assert reminded["delivery"]["reminders"][0]["delivery_status"] == "LINK_ROTATED_NOT_SENT_CHANNEL_NOT_CONFIGURED"
    assert reminded["secure_link"]["token"]


def test_optional_separate_channel_code_is_one_time_rotatable_and_required(tmp_path):
    service = LegalSigningService(tmp_path)
    created = service.create_envelope(
        "w", title="Higher assurance agreement", document_content="Exact terms",
        signers=[{
            "name": "A Person", "email": "a@example.com",
            "verification_method": "separate_channel_code",
        }], actor_id="owner",
    )
    assert created["signers"][0]["verification_method"] == "separate_channel_code"
    assert "verification_code_hash" not in created["signers"][0]
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    first = issued["secure_links"][0]
    assert first["verification_method"] == "separate_channel_code"
    assert len(first["verification_code"]) == 10
    assert "verification_code_hash" not in issued["signers"][0]
    assert service.signer_view(first["token"])["signer"]["verification_method"] == "separate_channel_code"

    with pytest.raises(LegalSigningError, match="separate_channel_verification_code"):
        service.sign(first["token"], "A Person", "a@example.com")
    with pytest.raises(LegalSigningError, match="separate_channel_verification_code"):
        service.sign(first["token"], "A Person", "a@example.com", "WRONG-CODE")

    reminded = service.record_reminder(
        "w", created["envelope_id"], "owner", issued["signers"][0]["signer_id"],
    )
    rotated = reminded["secure_link"]
    assert rotated["verification_code"] != first["verification_code"]
    with pytest.raises(LegalSigningError, match="secure_signing_link_invalid"):
        service.sign(first["token"], "A Person", "a@example.com", first["verification_code"])
    completed = service.sign(
        rotated["token"], "A Person", "a@example.com", rotated["verification_code"].lower(),
    )
    assert completed["status"] == "COMPLETED"
    assert completed["signers"][0]["signature_method"] == "typed_name_email_plus_separate_channel_code"
    stored = service._load("w", created["envelope_id"])
    assert stored["signers"][0]["token_hash"] is None
    assert stored["signers"][0]["verification_code_hash"] is None


def test_unknown_signer_verification_method_is_rejected(tmp_path):
    service = LegalSigningService(tmp_path)
    with pytest.raises(LegalSigningError, match="unsupported_signer_verification_method"):
        service.create_envelope(
            "w", title="Agreement", document_content="Terms",
            signers=[{
                "name": "A Person", "email": "a@example.com",
                "verification_method": "unverified_magic",
            }], actor_id="owner",
        )


def test_expiry_and_tamper_detection(tmp_path):
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    clock = [now]
    service = LegalSigningService(tmp_path, clock=lambda: clock[0])
    created = service.create_envelope("w", title="Quote", document_content="Quote terms", signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner", expires_in_days=1)
    clock[0] = now + timedelta(days=2)
    assert service.get_envelope("w", created["envelope_id"])["status"] == "EXPIRED"
    path = next((tmp_path / "w").glob("*.enc"))
    raw = service._read(path)
    raw["audit_events"][0]["actor_id"] = "tampered"
    service.store.write(path, raw, workspace_id="w", record_id=created["envelope_id"])
    assert service.verify_audit_chain("w", created["envelope_id"]) is False


def test_completed_envelope_creates_private_glyphchain_proof_receipt(tmp_path):
    service = LegalSigningService(tmp_path)
    created = service.create_envelope(
        "w", title="Private agreement", document_content="Terms known only to the parties",
        signers=[{"name": "Private Signer", "email": "private@example.com"}], actor_id="owner",
    )
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    completed = service.sign(issued["secure_links"][0]["token"], "Private Signer", "private@example.com")

    assert completed["glyphchain_proof"]["status"] == "PENDING_GLYPHCHAIN_SUBMISSION"
    assert completed["glyphchain_proof"]["requires_photon"] is False
    proof = service.document_proof("w", created["envelope_id"])
    public_payload = json.dumps(proof["glyphchain_payload"])
    assert "Terms known only to the parties" not in public_payload
    assert "Private Signer" not in public_payload
    assert "private@example.com" not in public_payload
    verification = service.verify_document_proof("w", created["envelope_id"], "Terms known only to the parties")
    assert verification["valid"] is True
    assert verification["private_signer_commitments_verified"] is True


def test_signing_key_rotation_preserves_verification_of_retired_receipts(tmp_path):
    service = LegalSigningService(tmp_path)

    def complete(title: str):
        created = service.create_envelope(
            "w", title=title, document_content=f"{title} terms",
            signers=[{"name": "Signer", "email": "signer@example.com"}], actor_id="owner",
        )
        pending = service.submit_for_approval("w", created["envelope_id"], "owner")
        service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
        issued = service.issue("w", created["envelope_id"], "owner")
        service.sign(issued["secure_links"][0]["token"], "Signer", "signer@example.com")
        return created["envelope_id"]

    old_id = complete("Old key document")
    old_proof = service.document_proof("w", old_id)
    service.key_store.rotate_signing_key()
    new_id = complete("New key document")
    new_proof = service.document_proof("w", new_id)

    assert old_proof["origin_device"]["key_version"] == 1
    assert new_proof["origin_device"]["key_version"] == 2
    assert old_proof["origin_device"]["key_id"] != new_proof["origin_device"]["key_id"]
    assert service.verify_document_proof("w", old_id, "Old key document terms")["valid"] is True
    assert service.verify_document_proof("w", new_id, "New key document terms")["valid"] is True


def test_completed_envelope_can_finalize_document_proof_on_glyphchain(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "0")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "ed25519")
    reset_ledger(clear_persist=False)
    chain_bank.reset_state()

    proof_service = LegalDocumentProofService(tmp_path, chain_submission_enabled=True)
    service = LegalSigningService(tmp_path, proof_service=proof_service)

    created = service.create_envelope(
        "w", title="Agreement", document_content="Final terms",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
    )
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    completed = service.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")

    assert completed["glyphchain_proof"]["status"] == "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY"
    assert completed["glyphchain_proof"]["tx_id"].startswith("tx_")
    verification = service.verify_document_proof("w", created["envelope_id"], "Final terms")
    assert verification["valid"] is True
    assert verification["glyphchain_inclusion_verified"] is True
    assert verification["glyphchain_transaction_payload_verified"] is True
    proof = service.document_proof("w", created["envelope_id"])
    assert proof["chain_context"] == {
        "network": "GlyphChain",
        "chain_id": "glyphchain-dev",
        "network_id": "devnet",
        "protocol_version": "glyphchain-document-proof-v1",
        "transaction_hash_version": "glyphchain-ledger-envelope-sha256-v1",
    }
    assert proof["glyphchain"]["transaction_envelope"]["payload"] == proof["glyphchain_payload"]

    tampered = json.loads(json.dumps(proof))
    tampered["glyphchain"]["transaction_envelope"]["payload"]["document_hash"] = "0" * 64
    rejected = proof_service.verify_bundle(tampered, document_content="Final terms")
    assert rejected["valid"] is False
    assert "glyphchain_transaction_payload_mismatch" in rejected["errors"]

    reset_ledger(clear_persist=False)
    chain_bank.reset_state()


def test_proof_receipt_cannot_appoint_its_own_finality_trust_anchor(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "0")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "ed25519")
    monkeypatch.delenv("GLYPHCHAIN_FINALITY_CHECKPOINT_PATH", raising=False)
    monkeypatch.delenv("GLYPHCHAIN_FINALITY_CHECKPOINT_JSON", raising=False)
    reset_ledger(clear_persist=False)
    chain_bank.reset_state()

    proof_service = LegalDocumentProofService(tmp_path, chain_submission_enabled=True)
    service = LegalSigningService(tmp_path, proof_service=proof_service)
    created = service.create_envelope(
        "w", title="Agreement", document_content="Trust boundary terms",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
    )
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    service.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")
    proof = service.document_proof("w", created["envelope_id"])

    keys = [Ed25519PrivateKey.generate() for _ in range(3)]
    validators = [{
        "validator_id": f"v{index + 1}",
        "power": 1,
        "public_key_base64": base64.b64encode(key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )).decode("ascii"),
    } for index, key in enumerate(keys)]
    certificate = build_finality_certificate(
        chain_id="glyphchain-dev", network_id="devnet",
        height=int(proof["glyphchain"]["block_height"]), round=0,
        block_id=f"consensus-block-C{'11' * 32}", validator_set=validators, votes=[],
        checkpoint_id="checkpoint-from-receipt",
        ledger_commitment="11" * 32,
        txs_root=proof["glyphchain"]["txs_root"],
    )
    certificate["votes"] = [{
        "validator_id": validators[index]["validator_id"],
        "signature_base64": base64.b64encode(keys[index].sign(
            vote_sign_bytes(certificate, validators[index]["validator_id"])
        )).decode("ascii"),
    } for index in (0, 1)]
    proof["glyphchain"]["quorum_finality_certificate"] = certificate
    proof["glyphchain"]["ledger_commitment"] = certificate["ledger_commitment"]
    proof["glyphchain"]["block_id"] = certificate["block_id"]
    proof["glyphchain"]["trusted_validator_set_root"] = certificate["validator_set_root"]

    unanchored = proof_service.verify_bundle(proof, document_content="Trust boundary terms")
    assert unanchored["valid"] is True
    assert unanchored["glyphchain_quorum_finality_verified"] is None
    assert unanchored["glyphchain_quorum_finality_assurance"] == "CERTIFICATE_INTEGRITY_ONLY"

    anchored = proof_service.verify_bundle(
        proof,
        document_content="Trust boundary terms",
        trusted_validator_set_root=certificate["validator_set_root"],
    )
    assert anchored["valid"] is True
    assert anchored["glyphchain_quorum_finality_verified"] is True
    assert anchored["glyphchain_quorum_finality_assurance"] == "TRUST_ANCHORED"

    wrong = proof_service.verify_bundle(
        proof,
        document_content="Trust boundary terms",
        trusted_validator_set_root="0" * 64,
    )
    assert wrong["valid"] is False
    assert wrong["glyphchain_quorum_finality_verified"] is False
    assert "glyphchain_quorum_finality_invalid" in wrong["errors"]

    reset_ledger(clear_persist=False)
    chain_bank.reset_state()


def test_failed_proof_submission_is_durable_and_recovers_after_restart(tmp_path):
    calls = []

    def unavailable(payload, private_key):
        calls.append(payload["proof_id"])
        raise RuntimeError("network temporarily unavailable")

    failing_proof_service = LegalDocumentProofService(
        tmp_path,
        chain_submitter=unavailable,
        chain_submission_enabled=True,
    )
    signing = LegalSigningService(tmp_path, proof_service=failing_proof_service)
    created = signing.create_envelope(
        "w", title="Agreement", document_content="Durable proof terms",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
    )
    pending = signing.submit_for_approval("w", created["envelope_id"], "owner")
    signing.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = signing.issue("w", created["envelope_id"], "owner")
    completed = signing.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")

    assert completed["glyphchain_proof"]["status"] == "SUBMISSION_FAILED_RETRY_AVAILABLE"
    queued = failing_proof_service.outbox_status()
    assert queued["counts"] == {"RETRY_PENDING": 1}
    assert queued["items"][0]["attempt_count"] == 1
    assert "network temporarily unavailable" in queued["items"][0]["last_error"]

    def recovered(payload, private_key):
        calls.append(payload["proof_id"])
        return {
            "applied": True,
            "tx_id": "tx_recovered",
            "tx_hash": "ab" * 32,
            "block_height": 9,
            "tx_index": 0,
            "txs_root": "cd" * 32,
            "proof": [],
        }

    restarted = LegalDocumentProofService(tmp_path, chain_submitter=recovered)
    retried = restarted.retry_due(force=True)
    assert retried["attempted_count"] == 1
    assert retried["attempted"][0]["status"] == "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY"
    assert retried["counts"] == {"LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY": 1}
    receipt = restarted.bundle_for_envelope("w", created["envelope_id"])
    assert receipt["glyphchain"]["tx_id"] == "tx_recovered"
    assert len(calls) == 2

    journal = (tmp_path / "_proof_outbox" / "events.jsonl").read_text(encoding="utf-8")
    assert '"event": "ENQUEUED"' in journal
    assert '"event": "RETRY_PENDING"' in journal
    assert '"event": "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY"' in journal


def test_ledger_committed_proof_submission_is_idempotent_while_finality_is_pending(tmp_path):
    calls = []

    def submit(payload, private_key):
        calls.append(payload["proof_id"])
        return {
            "applied": True,
            "tx_id": "tx_once",
            "tx_hash": "ab" * 32,
            "block_height": 2,
            "tx_index": 0,
            "txs_root": "cd" * 32,
            "proof": [],
        }

    proof_service = LegalDocumentProofService(tmp_path, chain_submitter=submit)
    signing = LegalSigningService(tmp_path, proof_service=proof_service)
    created = signing.create_envelope(
        "w", title="Agreement", document_content="One proof only",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
    )
    pending = signing.submit_for_approval("w", created["envelope_id"], "owner")
    signing.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = signing.issue("w", created["envelope_id"], "owner")
    signing.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")

    first = signing.submit_document_proof("w", created["envelope_id"])
    second = signing.submit_document_proof("w", created["envelope_id"])
    assert first["glyphchain"]["tx_id"] == "tx_once"
    assert second["glyphchain"]["tx_id"] == "tx_once"
    assert calls == [first["glyphchain_payload"]["proof_id"]]
    assert proof_service.outbox_status()["counts"] == {"LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY": 1}


def test_completed_envelope_exports_private_evidence_package(tmp_path):
    service = LegalSigningService(tmp_path)
    created = service.create_envelope(
        "w", title="Private Service Agreement", document_content="Exact private agreement terms",
        signers=[{"name": "A Person", "email": "a@example.com", "role": "Customer"}], actor_id="owner",
    )
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    service.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")

    filename, body = service.build_evidence_package("w", created["envelope_id"])
    assert filename.endswith(".tessaris-evidence.zip")
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        names = set(archive.namelist())
        assert "document.txt" in names
        assert "signed-document.html" in names
        assert "evidence-certificate.json" in names
        assert "audit-events.json" in names
        assert "document-history.json" in names
        proof_name = next(name for name in names if name.endswith(".tessaris-proof"))
        assert archive.read("document.txt").decode() == "Exact private agreement terms"
        certificate = json.loads(archive.read("evidence-certificate.json"))
        signed_document = archive.read("signed-document.html").decode("utf-8")
        assert "TESSARIS · COMPLETED SIGNED DOCUMENT" in signed_document
        assert "&lt;script&gt;" not in signed_document
        assert certificate["document"]["sha256"] in signed_document
        proof = json.loads(archive.read(proof_name))
        assert certificate["audit_chain_valid_at_export"] is True
        assert json.loads(archive.read("document-history.json"))["history_links_valid"] is True
        assert certificate["glyphchain"]["proof_id"] == proof["glyphchain_payload"]["proof_id"]
        assert "qualified electronic signature" in certificate["not_a_claim_of"]


def test_completed_envelope_retention_hold_export_and_guarded_deletion(tmp_path):
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    service = LegalSigningService(tmp_path, clock=lambda: now)
    created = service.create_envelope(
        "w", title="Deletable agreement", document_content="Private retained terms",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
    )
    envelope_id = created["envelope_id"]
    pending = service.submit_for_approval("w", envelope_id, "owner")
    service.approve("w", envelope_id, "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", envelope_id, "owner")
    service.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")
    service.update_records_governance(
        "w", envelope_id, actor_id="owner", retain_until="2026-09-25T12:00:00Z",
        legal_hold=True, legal_hold_reason="Active evidence preservation notice",
    )
    service.build_evidence_package("w", envelope_id, "owner")
    with pytest.raises(LegalSigningError, match="legal_hold"):
        service.destroy_envelope(
            "w", envelope_id, actor_id="owner", confirmation=f"DELETE {envelope_id}",
        )
    service.update_records_governance("w", envelope_id, actor_id="owner", legal_hold=False)
    receipt = service.destroy_envelope(
        "w", envelope_id, actor_id="owner", confirmation=f"DELETE {envelope_id}",
    )
    assert receipt["record_type"] == "signature_envelope"
    assert receipt["document_sha256"] == created["document"]["content_hash"]
    assert "Private retained terms" not in json.dumps(receipt)
    assert next((tmp_path / "w" / "_destruction").glob("*.enc"))
    with pytest.raises(LegalSigningError, match="envelope_not_found"):
        service.get_envelope("w", envelope_id)


def test_completed_replacement_supersedes_without_rewriting_prior_evidence(tmp_path):
    service = LegalSigningService(tmp_path)

    original = service.create_envelope(
        "w", title="Service terms v1", document_content="Original terms",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
    )
    pending = service.submit_for_approval("w", original["envelope_id"], "owner")
    service.approve("w", original["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", original["envelope_id"], "owner")
    completed_original = service.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")
    original_manifest = completed_original["signed_copy"]["manifest_hash"]

    replacement = service.create_envelope(
        "w", title="Service terms v2", document_content="Replacement terms",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
        supersedes_envelope_id=original["envelope_id"],
    )
    pending = service.submit_for_approval("w", replacement["envelope_id"], "owner")
    service.approve("w", replacement["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", replacement["envelope_id"], "owner")
    completed_replacement = service.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")

    stored_original = service.get_envelope("w", original["envelope_id"])
    assert stored_original["signed_copy"]["manifest_hash"] == original_manifest
    assert stored_original["lifecycle"]["status"] == "SUPERSEDED"
    assert stored_original["lifecycle"]["superseded_by_envelope_id"] == replacement["envelope_id"]
    assert completed_replacement["lifecycle"]["status"] == "ACTIVE"
    assert completed_replacement["lifecycle"]["supersedes_manifest_hash"] == original_manifest

    history = service.document_history("w", replacement["envelope_id"])
    assert history["history_links_valid"] is True
    assert history["all_audit_chains_valid"] is True
    assert history["all_available_proofs_valid"] is True
    assert [item["envelope_id"] for item in history["newest_to_oldest"]] == [
        replacement["envelope_id"], original["envelope_id"],
    ]


def test_lifecycle_notice_is_non_destructive_and_requires_acknowledgement(tmp_path):
    service = LegalSigningService(tmp_path)
    created = service.create_envelope(
        "w", title="Agreement", document_content="Terms",
        signers=[{"name": "A Person", "email": "a@example.com"}], actor_id="owner",
    )
    pending = service.submit_for_approval("w", created["envelope_id"], "owner")
    service.approve("w", created["envelope_id"], "owner", pending["approval"]["review_hash"])
    issued = service.issue("w", created["envelope_id"], "owner")
    completed = service.sign(issued["secure_links"][0]["token"], "A Person", "a@example.com")

    with pytest.raises(LegalSigningError, match="acknowledgement"):
        service.record_lifecycle_notice(
            "w", created["envelope_id"], "owner", notice_type="TERMINATED",
            reason="Ended by mutual agreement", effective_at="2026-10-01",
        )

    ended = service.record_lifecycle_notice(
        "w", created["envelope_id"], "owner", notice_type="TERMINATED",
        reason="Ended by mutual agreement", effective_at="2026-10-01",
        reference="termination-letter-001", acknowledge_preserved_evidence=True,
    )
    assert ended["status"] == "COMPLETED"
    assert ended["signed_copy"]["manifest_hash"] == completed["signed_copy"]["manifest_hash"]
    assert ended["lifecycle"]["status"] == "TERMINATED"
    assert ended["lifecycle"]["notices"][0]["preserves_original_evidence"] is True
    assert service.verify_audit_chain("w", created["envelope_id"]) is True
