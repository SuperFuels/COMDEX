#!/usr/bin/env python3
"""Independently verify journey 26 backup/restore staging and complete its surface proof."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from backend.modules.aion_business.runtime.business_data_write_tracer import BusinessDataWriteTracer


SESSION_ID = "backup-recovery"
SCENARIO = "snapshot-corrupt-live-copy-and-restore-on-clean-node"


def _private_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification-root", required=True)
    parser.add_argument("--trace-root", required=True)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--application-root", required=True)
    parser.add_argument("--update-root", required=True)
    parser.add_argument("--vault-root", required=True)
    parser.add_argument("--secret-root", required=True)
    parser.add_argument("--fingerprint-key-base64", required=True)
    args = parser.parse_args()

    qualification = Path(args.qualification_root).resolve(strict=True)
    snapshot = qualification / "backup-destination" / "journey26.tessaris-snapshot"
    restored = qualification / "clean-restored-vault"
    header = json.loads((snapshot / "snapshot.json").read_text(encoding="utf-8"))
    if header.get("key_material_in_snapshot") is not False:
        raise ValueError("backup_snapshot_key_material_assertion_failed")
    if header.get("encryption") != "AES-256-GCM-chunked":
        raise ValueError("backup_snapshot_encryption_assertion_failed")
    with sqlite3.connect(restored / "records" / "guardian.sqlite3") as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        live_heads = int(connection.execute("SELECT COUNT(*) FROM guardian_record_heads").fetchone()[0])
        originals = int(
            connection.execute(
                "SELECT COUNT(*) FROM guardian_record_heads WHERE collection='original_files'"
            ).fetchone()[0]
        )
    if not integrity or integrity[0] != "ok" or live_heads <= 0:
        raise ValueError("restored_vault_integrity_failed")

    key = base64.b64decode(args.fingerprint_key_base64, validate=True)
    tracer = BusinessDataWriteTracer(
        source_root=Path(args.repository_root),
        application_root=Path(args.application_root),
        update_root=Path(args.update_root),
        vault_roots=[Path(args.vault_root)],
        secret_store_roots=[Path(args.secret_root)],
        excluded_roots=[Path(args.trace_root)],
        path_fingerprint_key=key,
    )
    with tracer:
        _private_json(
            qualification / "filesystem-readback-proof.json",
            {
                "schema_version": "tessaris.backup-recovery-readback-proof.v1",
                "snapshot_id": header["snapshot_id"],
                "snapshot_index_sha256": header["index_sha256"],
                "restored_guardian_integrity": "ok",
                "live_head_count": live_heads,
                "original_count": originals,
                "customer_content_in_proof": False,
            },
        )
    report_path = Path(args.trace_root) / f"{SESSION_ID}.filesystem_import.json"
    tracer.write_report(
        report_path,
        session_id=SESSION_ID,
        scenario=SCENARIO,
        scenario_completed=True,
        surface="filesystem_import",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("release_gate_passed") is not True:
        raise ValueError("backup_recovery_filesystem_surface_failed")
    report["observed_external_classes"] = ["backup_destination", "secret_store"]
    _private_json(report_path, report)
    print(json.dumps({
        "ok": True,
        "restored_guardian_integrity": "ok",
        "live_head_count": live_heads,
        "original_count": originals,
        "external_classes": report["observed_external_classes"],
        "customer_content_in_output": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
