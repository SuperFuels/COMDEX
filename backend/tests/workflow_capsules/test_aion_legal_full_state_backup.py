from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import base64

import pytest

from backend.modules.aion_business.runtime.legal_delivery_service import LegalDeliveryService
from backend.modules.aion_business.runtime.legal_document_service import LegalDocumentService
from backend.modules.aion_business.runtime.legal_full_state_backup import (
    LegalFullStateBackupError,
    LegalFullStateBackupService,
    LegalFullStateLayout,
)
from backend.modules.aion_business.runtime.legal_matter_service import LegalMatterService
from backend.modules.aion_business.runtime.legal_signing_service import LegalSigningService
from backend.modules.aion_business.runtime.legal_template_service import LegalTemplateService
from backend.modules.p2p.network_identity import NetworkIdentityStore
from backend.modules.consensus.finality_checkpoint import normalize_checkpoint


PASSWORD = "correct horse battery staple for recovery"


def _layout(root: Path) -> LegalFullStateLayout:
    legal = root / "legal"
    return LegalFullStateLayout(
        legal_roots={
            "signing": legal / "signing",
            "matters": legal / "matters",
            "documents": legal / "documents",
            "templates": legal / "templates",
        },
        glyphchain_state_root=root / "glyphchain-state",
        ledger_database=root / "ledger" / "chain.sqlite3",
        network_identity_root=root / "glyphchain-state" / "network-identity",
        chain_id="glyphchain-recovery-test",
        node_id="node-recovery-a",
        checkpoint_path=root / "trust" / "checkpoint.json",
        independent_pin_path=root / "trust" / "pin.json",
    )


def _populate(layout: LegalFullStateLayout) -> dict[str, str]:
    workspace = "home-fixed"
    signing = LegalSigningService(layout.legal_roots["signing"])
    envelope = signing.create_envelope(
        workspace,
        title="Recovery agreement",
        document_content="Confidential terms that must remain encrypted.",
        signers=[{"name": "Ada Person", "email": "ada@example.com"}],
        actor_id="owner",
    )
    matter = LegalMatterService(layout.legal_roots["matters"]).create_matter(
        workspace,
        title="Recovery matter",
        counterparty="Example Limited",
        matter_type="CONTRACT",
        risk="NORMAL",
        summary="Preserve the evidence.",
        jurisdiction={
            "country_code": "IE",
            "region": "",
            "governing_law": "Laws of Ireland",
            "forum": "Courts of Ireland",
            "owner_confirmed": True,
        },
        actor_id="owner",
    )
    document = LegalDocumentService(layout.legal_roots["documents"]).ingest(
        workspace,
        filename="terms.txt",
        media_type="text/plain",
        content=b"These are confidential contract terms.",
        actor_id="owner",
        matter_id=matter["matter_id"],
    )
    template = LegalTemplateService(layout.legal_roots["templates"]).create_draft(
        workspace,
        title="Recovery template",
        template_type="CUSTOMER_AGREEMENT",
        jurisdiction={
            "country_code": "IE",
            "region": "",
            "governing_law": "Laws of Ireland",
            "forum": "Courts of Ireland",
            "owner_confirmed": True,
        },
        content="Agreement with {{customer_name}}",
        intended_use="Testing recovery only",
        actor_id="owner",
    )
    delivery = LegalDeliveryService(layout.legal_roots["signing"])
    queued = delivery.queue(
        workspace,
        envelope_id=envelope["envelope_id"],
        manifest_hash="a" * 64,
        signer={"signer_id": "signer-recovery", "email": "ada@example.com"},
        provider="resend",
        subject="Signed copy",
        body_text="Your signed copy",
        attachment_name="evidence.zip",
        attachment_bytes=b"private evidence",
        approved_by="owner",
        acknowledge_external_send=True,
    )
    proof_outbox = layout.legal_roots["signing"] / "_proof_outbox"
    (proof_outbox / "items").mkdir(parents=True, exist_ok=True)
    (proof_outbox / "items" / "proof-recovery.json").write_text(
        json.dumps({"proof_id": "proof-recovery", "status": "RETRY_PENDING"}), encoding="utf-8",
    )
    (proof_outbox / "events.jsonl").write_text(
        json.dumps({"proof_id": "proof-recovery", "event": "ENQUEUED"}) + "\n", encoding="utf-8",
    )
    legacy_private = layout.legal_roots["signing"] / "_device_identity" / "legal-proof-ed25519.pem"
    legacy_private.parent.mkdir(parents=True, exist_ok=True)
    legacy_private.write_text("LEGACY PRIVATE KEY MUST NOT BE COPIED", encoding="utf-8")

    layout.glyphchain_state_root.mkdir(parents=True, exist_ok=True)
    (layout.glyphchain_state_root / "consensus_state.json").write_text(
        json.dumps({"height": 42, "locked_round": 4}), encoding="utf-8",
    )
    layout.ledger_database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(layout.ledger_database)
    try:
        connection.execute("CREATE TABLE proofs (id TEXT PRIMARY KEY, status TEXT NOT NULL)")
        connection.execute("INSERT INTO proofs VALUES ('proof-recovery', 'FINALIZED')")
        connection.commit()
    finally:
        connection.close()
    layout.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = normalize_checkpoint({
        "schema_version": "glyphchain.validator-set-checkpoint.v1",
        "chain_id": layout.chain_id,
        "network_id": "recovery-testnet",
        "epoch": 0,
        "effective_height": 1,
        "validator_set": [{
            "validator_id": "validator-a",
            "power": 1,
            "public_key_base64": base64.b64encode(b"v" * 32).decode("ascii"),
        }],
    })
    layout.checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    layout.independent_pin_path.write_text(
        json.dumps({"checkpoint_id": checkpoint["checkpoint_id"]}), encoding="utf-8",
    )
    identity = NetworkIdentityStore(
        layout.network_identity_root,
        chain_id=layout.chain_id,
        node_id=layout.node_id,
        runtime_mode="test",
    ).identity()
    return {
        "workspace": workspace,
        "envelope_id": envelope["envelope_id"],
        "matter_id": matter["matter_id"],
        "document_id": document["document_id"],
        "template_id": template["template_id"],
        "delivery_id": queued["delivery_id"],
        "network_key_id": identity["key_id"],
        "checkpoint_id": checkpoint["checkpoint_id"],
    }


def test_encrypted_full_state_backup_restores_clean_device_and_authenticates_state(tmp_path):
    source_layout = _layout(tmp_path / "source")
    expected = _populate(source_layout)
    backup = tmp_path / "device.tessaris-backup"
    created = LegalFullStateBackupService(source_layout).create_backup(
        backup,
        password=PASSWORD,
        workspace_id=expected["workspace"],
        actor_id="owner@example.com",
        confirmation="EXPORT COMPLETE LEGAL AND GLYPHCHAIN STATE",
    )
    assert created["verified"] is True
    assert created["ledger_present"] is True
    assert created["checkpoint_present"] is True
    assert created["independent_pin_present"] is True
    assert created["network_identity_recovery_present"] is True
    assert created["raw_private_keys_exposed"] is False
    assert b"Confidential terms that must remain encrypted" not in backup.read_bytes()

    restored_layout = _layout(tmp_path / "restored")
    result = LegalFullStateBackupService(restored_layout).restore_backup(
        backup,
        password=PASSWORD,
        actor_id="restoring-owner",
        confirmation="RESTORE COMPLETE LEGAL AND GLYPHCHAIN STATE",
    )
    assert result["restored"] is True
    assert result["restart_required"] is True
    assert result["safety_copies"] == []
    assert result["restored_state"]["encrypted_records_authenticated"] >= 5
    assert result["restored_state"]["signing_audit_chains_verified"] == 1
    assert result["restored_state"]["matter_audit_chains_verified"] == 1
    assert result["restored_state"]["delivery_event_chains_verified"] == 1
    assert result["restored_state"]["ledger_integrity"] == "ok"
    assert result["restored_state"]["network_identity_rotation_chain_valid"] is True
    recovery_events = [
        json.loads(line)
        for line in (restored_layout.glyphchain_state_root / "device-recovery-audit.jsonl").read_text().splitlines()
    ]
    assert [event["event_type"] for event in recovery_events] == ["EXPORT_STARTED", "RESTORE_COMPLETED"]

    signing = LegalSigningService(restored_layout.legal_roots["signing"])
    assert signing.get_envelope(expected["workspace"], expected["envelope_id"])["title"] == "Recovery agreement"
    assert signing.verify_audit_chain(expected["workspace"], expected["envelope_id"])
    matters = LegalMatterService(restored_layout.legal_roots["matters"])
    assert matters.get_matter(expected["workspace"], expected["matter_id"])["title"] == "Recovery matter"
    assert matters.verify_audit_chain(expected["workspace"], expected["matter_id"])
    assert LegalDocumentService(restored_layout.legal_roots["documents"]).get_document(
        expected["workspace"], expected["document_id"], include_text=True,
    )["filename"] == "terms.txt"
    assert LegalTemplateService(restored_layout.legal_roots["templates"]).get_template(
        expected["workspace"], expected["template_id"],
    )["title"] == "Recovery template"
    assert LegalDeliveryService(restored_layout.legal_roots["signing"]).status(expected["workspace"])["items"][0]["delivery_id"] == expected["delivery_id"]
    assert (restored_layout.legal_roots["signing"] / "_proof_outbox" / "items" / "proof-recovery.json").is_file()
    assert not (restored_layout.legal_roots["signing"] / "_device_identity" / "legal-proof-ed25519.pem").exists()
    assert json.loads((restored_layout.glyphchain_state_root / "consensus_state.json").read_text())["height"] == 42
    connection = sqlite3.connect(restored_layout.ledger_database)
    try:
        assert connection.execute("SELECT status FROM proofs WHERE id='proof-recovery'").fetchone()[0] == "FINALIZED"
    finally:
        connection.close()
    assert json.loads(restored_layout.checkpoint_path.read_text())["checkpoint_id"] == expected["checkpoint_id"]
    assert NetworkIdentityStore(
        restored_layout.network_identity_root,
        chain_id=restored_layout.chain_id,
        node_id=restored_layout.node_id,
        runtime_mode="test",
    ).identity()["key_id"] == expected["network_key_id"]


def test_full_state_backup_rejects_wrong_password_tampering_and_silent_overwrite(tmp_path):
    source_layout = _layout(tmp_path / "source")
    expected = _populate(source_layout)
    backup = tmp_path / "device.tessaris-backup"
    service = LegalFullStateBackupService(source_layout)
    service.create_backup(
        backup,
        password=PASSWORD,
        workspace_id=expected["workspace"],
        actor_id="owner",
        confirmation="EXPORT COMPLETE LEGAL AND GLYPHCHAIN STATE",
    )
    with pytest.raises(PermissionError, match="could not be authenticated"):
        service.inspect_backup(backup, password="wrong password but long enough")

    tampered = tmp_path / "tampered.tessaris-backup"
    raw = bytearray(backup.read_bytes())
    raw[-20] ^= 1
    tampered.write_bytes(raw)
    with pytest.raises((PermissionError, LegalFullStateBackupError)):
        service.inspect_backup(tampered, password=PASSWORD)

    restored_layout = _layout(tmp_path / "occupied")
    restored_layout.glyphchain_state_root.mkdir(parents=True)
    (restored_layout.glyphchain_state_root / "do-not-replace.txt").write_text("existing", encoding="utf-8")
    with pytest.raises(LegalFullStateBackupError, match="restore_target_not_empty"):
        LegalFullStateBackupService(restored_layout).restore_backup(
            backup,
            password=PASSWORD,
            actor_id="restoring-owner",
            confirmation="RESTORE COMPLETE LEGAL AND GLYPHCHAIN STATE",
        )
    assert (restored_layout.glyphchain_state_root / "do-not-replace.txt").read_text() == "existing"


def test_full_state_restore_requires_exact_confirmation_and_strong_password(tmp_path):
    layout = _layout(tmp_path / "source")
    service = LegalFullStateBackupService(layout)
    with pytest.raises(LegalFullStateBackupError, match="confirmation"):
        service.create_backup(
            tmp_path / "backup",
            password=PASSWORD,
            workspace_id="home-fixed",
            actor_id="owner",
            confirmation="yes",
        )
    with pytest.raises(LegalFullStateBackupError, match="minimum_16"):
        service.create_backup(
            tmp_path / "backup",
            password="short password",
            workspace_id="home-fixed",
            actor_id="owner",
            confirmation="EXPORT COMPLETE LEGAL AND GLYPHCHAIN STATE",
        )
