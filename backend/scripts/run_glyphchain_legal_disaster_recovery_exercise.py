#!/usr/bin/env python3
"""Run a content-free Legal/GlyphChain disaster-recovery exercise.

The exercise creates synthetic encrypted Legal records and GlyphChain state,
exports one authenticated whole-device recovery package, proves common failure
paths are rejected, restores onto a clean layout, and runs the separate
compromised/lost-validator governance exercise.  The emitted report contains
only identifiers, digests, counts and boolean results; it never includes Legal
document content, passwords or private keys.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import secrets
import sqlite3
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
from backend.modules.consensus.finality_checkpoint import normalize_checkpoint
from backend.modules.p2p.network_identity import NetworkIdentityStore
from backend.scripts.run_glyphchain_validator_removal_exercise import (
    run_exercise as run_validator_removal_exercise,
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _implementation_manifest() -> dict[str, Any]:
    paths = [
        Path(__file__).resolve(),
        ROOT / "backend" / "scripts" / "run_glyphchain_validator_removal_exercise.py",
        ROOT / "backend" / "modules" / "aion_business" / "runtime" / "legal_full_state_backup.py",
        ROOT / "backend" / "modules" / "consensus" / "validator_governance.py",
        ROOT / "backend" / "modules" / "p2p" / "network_identity.py",
    ]
    files = []
    for path in paths:
        content = path.read_bytes()
        files.append({
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": len(content),
            "sha256": sha256(content).hexdigest(),
        })
    return {
        "files": files,
        "files_sha256": sha256(_canonical(files)).hexdigest(),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


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
        chain_id="glyphchain-recovery-exercise",
        node_id="exercise-node-a",
        checkpoint_path=root / "trust" / "checkpoint.json",
        independent_pin_path=root / "trust" / "pin.json",
    )


def _populate(layout: LegalFullStateLayout) -> dict[str, str]:
    workspace = "recovery-exercise"
    envelope = LegalSigningService(layout.legal_roots["signing"]).create_envelope(
        workspace,
        title="Synthetic recovery agreement",
        document_content="Synthetic confidential recovery content.",
        signers=[{"name": "Exercise Signer", "email": "signer@example.invalid"}],
        actor_id="exercise-owner",
    )
    matter = LegalMatterService(layout.legal_roots["matters"]).create_matter(
        workspace,
        title="Synthetic recovery matter",
        counterparty="Example Invalid",
        matter_type="CONTRACT",
        risk="NORMAL",
        summary="Synthetic recovery evidence only.",
        jurisdiction={
            "country_code": "IE",
            "region": "",
            "governing_law": "Laws of Ireland",
            "forum": "Courts of Ireland",
            "owner_confirmed": True,
        },
        actor_id="exercise-owner",
    )
    document = LegalDocumentService(layout.legal_roots["documents"]).ingest(
        workspace,
        filename="synthetic-terms.txt",
        media_type="text/plain",
        content=b"Synthetic confidential contract terms.",
        actor_id="exercise-owner",
        matter_id=matter["matter_id"],
    )
    template = LegalTemplateService(layout.legal_roots["templates"]).create_draft(
        workspace,
        title="Synthetic recovery template",
        template_type="CUSTOMER_AGREEMENT",
        jurisdiction={
            "country_code": "IE",
            "region": "",
            "governing_law": "Laws of Ireland",
            "forum": "Courts of Ireland",
            "owner_confirmed": True,
        },
        content="Synthetic agreement with {{CUSTOMER_NAME}}",
        intended_use="Recovery exercise only",
        actor_id="exercise-owner",
    )
    delivery = LegalDeliveryService(layout.legal_roots["signing"]).queue(
        workspace,
        envelope_id=envelope["envelope_id"],
        manifest_hash="a" * 64,
        signer={"signer_id": "exercise-signer", "email": "signer@example.invalid"},
        provider="resend",
        subject="Synthetic signed copy",
        body_text="Synthetic recovery delivery",
        attachment_name="synthetic-evidence.zip",
        attachment_bytes=b"synthetic private evidence",
        approved_by="exercise-owner",
        acknowledge_external_send=True,
    )

    proof_outbox = layout.legal_roots["signing"] / "_proof_outbox"
    (proof_outbox / "items").mkdir(parents=True, exist_ok=True)
    (proof_outbox / "items" / "proof-exercise.json").write_text(
        json.dumps({"proof_id": "proof-exercise", "status": "RETRY_PENDING"}),
        encoding="utf-8",
    )
    (proof_outbox / "events.jsonl").write_text(
        json.dumps({"proof_id": "proof-exercise", "event": "ENQUEUED"}) + "\n",
        encoding="utf-8",
    )
    legacy_private = layout.legal_roots["signing"] / "_device_identity" / "legal-proof-ed25519.pem"
    legacy_private.parent.mkdir(parents=True, exist_ok=True)
    legacy_private.write_text("SYNTHETIC PRIVATE KEY MUST NOT BE COPIED", encoding="utf-8")

    layout.glyphchain_state_root.mkdir(parents=True, exist_ok=True)
    (layout.glyphchain_state_root / "consensus_state.json").write_text(
        json.dumps({"height": 42, "locked_round": 4}), encoding="utf-8",
    )
    layout.ledger_database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(layout.ledger_database)
    try:
        connection.execute("CREATE TABLE proofs (id TEXT PRIMARY KEY, status TEXT NOT NULL)")
        connection.execute("INSERT INTO proofs VALUES ('proof-exercise', 'FINALIZED')")
        connection.commit()
    finally:
        connection.close()

    layout.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = normalize_checkpoint({
        "schema_version": "glyphchain.validator-set-checkpoint.v1",
        "chain_id": layout.chain_id,
        "network_id": "recovery-exercise-network",
        "epoch": 0,
        "effective_height": 1,
        "validator_set": [{
            "validator_id": "exercise-validator-a",
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
        "delivery_id": delivery["delivery_id"],
        "network_key_id": identity["key_id"],
        "checkpoint_id": checkpoint["checkpoint_id"],
    }


def _restored_checks(layout: LegalFullStateLayout, expected: dict[str, str]) -> dict[str, bool]:
    signing = LegalSigningService(layout.legal_roots["signing"])
    matters = LegalMatterService(layout.legal_roots["matters"])
    document = LegalDocumentService(layout.legal_roots["documents"]).get_document(
        expected["workspace"], expected["document_id"], include_text=False,
    )
    template = LegalTemplateService(layout.legal_roots["templates"]).get_template(
        expected["workspace"], expected["template_id"],
    )
    delivery = LegalDeliveryService(layout.legal_roots["signing"]).status(expected["workspace"])
    connection = sqlite3.connect(layout.ledger_database)
    try:
        ledger_status = connection.execute(
            "SELECT status FROM proofs WHERE id='proof-exercise'"
        ).fetchone()
    finally:
        connection.close()
    identity = NetworkIdentityStore(
        layout.network_identity_root,
        chain_id=layout.chain_id,
        node_id=layout.node_id,
        runtime_mode="test",
    ).identity()
    return {
        "signing_envelope_restored": (
            signing.get_envelope(expected["workspace"], expected["envelope_id"])["title"]
            == "Synthetic recovery agreement"
        ),
        "signing_audit_chain_valid": signing.verify_audit_chain(
            expected["workspace"], expected["envelope_id"]
        ),
        "legal_matter_restored": (
            matters.get_matter(expected["workspace"], expected["matter_id"])["title"]
            == "Synthetic recovery matter"
        ),
        "matter_audit_chain_valid": matters.verify_audit_chain(
            expected["workspace"], expected["matter_id"]
        ),
        "legal_document_restored": document["filename"] == "synthetic-terms.txt",
        "legal_template_restored": template["title"] == "Synthetic recovery template",
        "delivery_outbox_restored": any(
            item["delivery_id"] == expected["delivery_id"] for item in delivery["items"]
        ),
        "proof_outbox_restored": (
            layout.legal_roots["signing"] / "_proof_outbox" / "items" / "proof-exercise.json"
        ).is_file(),
        "raw_legacy_private_key_excluded": not (
            layout.legal_roots["signing"] / "_device_identity" / "legal-proof-ed25519.pem"
        ).exists(),
        "consensus_state_restored": json.loads(
            (layout.glyphchain_state_root / "consensus_state.json").read_text(encoding="utf-8")
        )["height"] == 42,
        "ledger_integrity_restored": bool(ledger_status and ledger_status[0] == "FINALIZED"),
        "checkpoint_restored": json.loads(layout.checkpoint_path.read_text(encoding="utf-8"))[
            "checkpoint_id"
        ] == expected["checkpoint_id"],
        "network_identity_restored": identity["key_id"] == expected["network_key_id"],
    }


def run_exercise() -> dict[str, Any]:
    started = time.monotonic()
    password = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="tessaris-disaster-recovery-exercise-") as temporary:
        root = Path(temporary)
        source = _layout(root / "source")
        expected = _populate(source)
        backup = root / "exercise.tessaris-backup"
        created = LegalFullStateBackupService(source).create_backup(
            backup,
            password=password,
            workspace_id=expected["workspace"],
            actor_id="exercise-owner",
            confirmation="EXPORT COMPLETE LEGAL AND GLYPHCHAIN STATE",
        )

        wrong_password_rejected = False
        try:
            LegalFullStateBackupService(source).inspect_backup(
                backup, password="wrong exercise password of sufficient length",
            )
        except PermissionError:
            wrong_password_rejected = True

        tampered = root / "tampered.tessaris-backup"
        tampered_bytes = bytearray(backup.read_bytes())
        tampered_bytes[-20] ^= 1
        tampered.write_bytes(tampered_bytes)
        tampered_backup_rejected = False
        try:
            LegalFullStateBackupService(source).inspect_backup(tampered, password=password)
        except (PermissionError, LegalFullStateBackupError):
            tampered_backup_rejected = True

        occupied = _layout(root / "occupied")
        occupied.glyphchain_state_root.mkdir(parents=True)
        occupied_marker = occupied.glyphchain_state_root / "do-not-replace.txt"
        occupied_marker.write_text("existing", encoding="utf-8")
        occupied_restore_rejected = False
        try:
            LegalFullStateBackupService(occupied).restore_backup(
                backup,
                password=password,
                actor_id="exercise-restorer",
                confirmation="RESTORE COMPLETE LEGAL AND GLYPHCHAIN STATE",
            )
        except LegalFullStateBackupError as exc:
            occupied_restore_rejected = "restore_target_not_empty" in str(exc)
        occupied_target_preserved = occupied_marker.read_text(encoding="utf-8") == "existing"

        restored = _layout(root / "restored")
        restore_result = LegalFullStateBackupService(restored).restore_backup(
            backup,
            password=password,
            actor_id="exercise-restorer",
            confirmation="RESTORE COMPLETE LEGAL AND GLYPHCHAIN STATE",
        )
        state_checks = _restored_checks(restored, expected)

    restore_elapsed = time.monotonic() - started
    validator_started = time.monotonic()
    validator_report = run_validator_removal_exercise()
    validator_elapsed = time.monotonic() - validator_started
    checks = {
        "backup_authenticated_after_creation": bool(created["verified"]),
        "backup_excludes_raw_private_keys": not bool(created["raw_private_keys_exposed"]),
        "wrong_password_rejected": wrong_password_rejected,
        "tampered_backup_rejected": tampered_backup_rejected,
        "occupied_restore_rejected": occupied_restore_rejected,
        "occupied_target_preserved": occupied_target_preserved,
        "clean_restore_verified": bool(restore_result["verified"] and restore_result["restored"]),
        "clean_restore_requires_restart": bool(restore_result["restart_required"]),
        "encrypted_records_authenticated": int(
            restore_result["restored_state"]["encrypted_records_authenticated"]
        ) >= 5,
        "restored_ledger_integrity_ok": (
            restore_result["restored_state"]["ledger_integrity"] == "ok"
        ),
        "restored_network_rotation_chain_valid": bool(
            restore_result["restored_state"]["network_identity_rotation_chain_valid"]
        ),
        **state_checks,
        "lost_or_compromised_validator_exercise_passed": validator_report["result"] == "PASS",
    }
    passed = all(checks.values())
    implementation = _implementation_manifest()
    report: dict[str, Any] = {
        "schema_version": "tessaris.legal-glyphchain-disaster-recovery-exercise.v1",
        "exercise_id": "exercise-legal-glyphchain-dr-001",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "result": "PASS" if passed else "FAIL",
        "claim_boundary": (
            "Local synthetic disaster-recovery and validator-governance exercise; "
            "not application-account recovery, representative-device testing, or production approval"
        ),
        "participants": ["automated local exercise runner"],
        "topology": {
            "recovery": "one synthetic source device, one occupied refusal target, one clean restore target",
            "validator_governance": "four current validators, one accused validator and one joining replacement",
            "external_network_used": False,
        },
        "inputs": {
            "fixture": "synthetic Legal records, delivery/proof outboxes, ledger, checkpoint and node identity",
            "backup_format": LegalFullStateBackupService.SCHEMA_VERSION,
            "validator_exercise_schema": validator_report["schema_version"],
        },
        "implementation": implementation,
        "observed_timings_seconds": {
            "backup_and_clean_restore": round(restore_elapsed, 6),
            "validator_removal": round(validator_elapsed, 6),
            "total": round(time.monotonic() - started, 6),
        },
        "checks": checks,
        "backup": {
            "file_count": int(created["file_count"]),
            "archive_sha256": created["archive_sha256"],
            "ledger_present": bool(created["ledger_present"]),
            "checkpoint_present": bool(created["checkpoint_present"]),
            "independent_pin_present": bool(created["independent_pin_present"]),
            "network_identity_recovery_present": bool(created["network_identity_recovery_present"]),
            "raw_private_keys_exposed": False,
        },
        "validator_exercise": {
            "result": validator_report["result"],
            "report_sha256": validator_report["report_sha256"],
            "checks": validator_report["checks"],
        },
        "findings": [],
        "finding_owners": [],
        "retest_evidence": {
            "automated_test": (
                "python -m pytest -q "
                "backend/tests/workflow_capsules/test_aion_legal_disaster_recovery_exercise.py"
            ),
            "exercise_command": (
                "python backend/scripts/run_glyphchain_legal_disaster_recovery_exercise.py "
                "--output <content-free-report.json>"
            ),
        },
        "password_exported": False,
        "private_keys_exported": False,
        "legal_document_content_present": False,
    }
    body = dict(report)
    report["report_sha256"] = sha256(_canonical(body)).hexdigest()
    if not passed:
        failed = ",".join(name for name, value in checks.items() if not value)
        raise RuntimeError(f"disaster recovery exercise failed:{failed}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_exercise()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    print(report["report_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
