from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .canonical import utc_now_iso
from .guardian_store import GuardianFabricStore
from .store import FabricStore


@dataclass(frozen=True, slots=True)
class FabricMigrationReceipt:
    source_path: str
    source_sha256: str
    source_size: int
    source_retained: bool
    source_counts: dict[str, int]
    target_counts: dict[str, int]
    migrated_records: int
    verified: bool
    completed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "tessaris.fabric-guardian-migration.v1",
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "source_size": self.source_size,
            "source_retained": self.source_retained,
            "source_counts": self.source_counts,
            "target_counts": self.target_counts,
            "migrated_records": self.migrated_records,
            "verified": self.verified,
            "completed_at": self.completed_at,
        }


_RECORD_TABLES = (
    ("nodes", "node_id", "record_json", "node"),
    ("capability_capsules", "capsule_id", "capsule_json", "capability"),
    ("delta_ledger", "packet_id", "packet_json", "delta"),
    ("discovery_runs", "run_id", "run_json", "discovery_run"),
    (
        "discovery_observations",
        "observation_id",
        "observation_json",
        "discovery_observation",
    ),
    ("device_schemas", "schema_id", "schema_json", "device_schema"),
    ("action_proposals", "proposal_id", "proposal_json", "action_proposal"),
    ("probe_receipts", "receipt_id", "receipt_json", "probe_receipt"),
    (
        "webos_pairing_receipts",
        "receipt_id",
        "receipt_json",
        "webos_pairing_receipt",
    ),
    (
        "webos_integration_receipts",
        "receipt_id",
        "receipt_json",
        "webos_integration_receipt",
    ),
    (
        "webos_action_receipts",
        "receipt_id",
        "receipt_json",
        "webos_action_receipt",
    ),
)


def legacy_source_sha256(path: str | Path) -> str:
    path = Path(path)
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def migration_receipt_entity_id(source_hash: str) -> str:
    return f"fabric.migration.{source_hash}"


def migrate_legacy_fabric_store(
    source: FabricStore,
    target: GuardianFabricStore,
) -> FabricMigrationReceipt:
    """Copy and verify one legacy Fabric database, leaving it untouched.

    This is deliberately a copy/verify operation. Deleting or archiving the
    source is a separate, explicit retention decision after acceptance testing.
    """

    source_path = source.path.resolve(strict=True)
    source_size = source_path.stat().st_size
    source_hash = legacy_source_sha256(source_path)
    source_counts = source.counts()
    migrated = 0

    with source.connect() as db:
        for table, identity_column, json_column, record_type in _RECORD_TABLES:
            rows = db.execute(
                f"SELECT {identity_column},{json_column} FROM {table}"
            ).fetchall()
            for row in rows:
                target._put_record(  # migration is the only bulk-loader
                    record_type,
                    str(row[identity_column]),
                    json.loads(row[json_column]),
                )
                migrated += 1

        for row in db.execute(
            "SELECT node_id,sequence,state_json,state_hash FROM node_state"
        ).fetchall():
            target._put_record(
                "node_state",
                str(row["node_id"]),
                {
                    "sequence": int(row["sequence"]),
                    "state": json.loads(row["state_json"]),
                    "state_hash": str(row["state_hash"]),
                },
            )
            migrated += 1

        for row in db.execute(
            "SELECT stream_id,node_id,start_sequence,end_sequence,stream_hash,accepted_at "
            "FROM stream_ledger"
        ).fetchall():
            target._put_record(
                "stream",
                str(row["stream_id"]),
                {
                    "stream_id": str(row["stream_id"]),
                    "node_id": str(row["node_id"]),
                    "start_sequence": int(row["start_sequence"]),
                    "end_sequence": int(row["end_sequence"]),
                    "payload_hash": str(row["stream_hash"]),
                    "accepted_at": str(row["accepted_at"]),
                    "legacy_metadata_only": True,
                },
            )
            migrated += 1

        checkpoint = db.execute(
            "SELECT checkpoint_json,anchor_hash,pruned_rows FROM audit_retention_checkpoint "
            "WHERE checkpoint_id=1"
        ).fetchone()
        events = []
        for row in db.execute(
            "SELECT event_json,event_hash FROM audit_ledger ORDER BY sequence"
        ).fetchall():
            event = json.loads(row["event_json"])
            event["event_hash"] = str(row["event_hash"])
            events.append(event)
        audit_state = {
            "schema_version": "tessaris.fabric-audit.v1",
            "events": events,
            "anchor_hash": str(checkpoint["anchor_hash"]) if checkpoint else "0" * 64,
            "pruned_event_count": int(checkpoint["pruned_rows"]) if checkpoint else 0,
        }
        existing = target.domain_store.get_optional(
            "security.audit",
            workspace_id=target.workspace_id,
            entity_id="fabric.audit-ledger",
        )
        target.domain_store.put(
            "security.audit",
            workspace_id=target.workspace_id,
            entity_id="fabric.audit-ledger",
            payload=audit_state,
            expected_version=int(existing["version"]) if existing else None,
        )

    target_counts = target.counts()
    comparable = set(source_counts) - {"audit_ledger"}
    counts_match = all(
        int(target_counts.get(name, -1)) == int(source_counts[name])
        for name in comparable
    )
    verified = (
        counts_match
        and target_counts["audit_ledger"] == source_counts["audit_ledger"]
        and target.verify_audit_chain()
        and source.verify_audit_chain()
        and source_path.exists()
        and source_path.stat().st_size == source_size
        and legacy_source_sha256(source_path) == source_hash
    )
    receipt = FabricMigrationReceipt(
        source_path=str(source_path),
        source_sha256=source_hash,
        source_size=source_size,
        source_retained=source_path.exists(),
        source_counts=source_counts,
        target_counts=target_counts,
        migrated_records=migrated,
        verified=verified,
        completed_at=utc_now_iso(),
    )
    target.domain_store.put(
        "security.audit",
        workspace_id=target.workspace_id,
        entity_id=migration_receipt_entity_id(source_hash),
        payload=receipt.to_dict(),
    )
    if not verified:
        raise RuntimeError("aion_fabric_guardian_migration_verification_failed")
    return receipt
