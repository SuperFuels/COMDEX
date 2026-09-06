from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .contracts import CapabilityCapsule, DeviceProfile, EnrollmentState, NodeRecord, NodeRole
from .delta import DeltaPacket, GlyphDeltaStream, apply_state_delta
from .discovery import DiscoveryObservation, DiscoveryRun
from .field_operator import FieldActionProposal
from .schema import ControlSurface, DeviceSchema, DocumentationArtifact
from .probe import ReadOnlyProbeReceipt
from .webos import WebOsActionReceipt, WebOsIntegrationReceipt, WebOsPairingReceipt


class FabricStore:
    DEFAULT_AUDIT_MAX_ROWS = 4096
    DEFAULT_AUDIT_PRUNE_TO_ROWS = 3072
    AUDIT_PRUNE_CHECK_INTERVAL = 256

    def __init__(
        self,
        path: str | Path,
        *,
        audit_max_rows: int = DEFAULT_AUDIT_MAX_ROWS,
        audit_prune_to_rows: int = DEFAULT_AUDIT_PRUNE_TO_ROWS,
    ) -> None:
        self.path = Path(path)
        if audit_max_rows < 2:
            raise ValueError("audit_max_rows must be at least 2")
        if not 1 <= audit_prune_to_rows < audit_max_rows:
            raise ValueError("audit_prune_to_rows must be positive and smaller than audit_max_rows")
        self.audit_max_rows = int(audit_max_rows)
        self.audit_prune_to_rows = int(audit_prune_to_rows)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS capability_capsules (
                    capsule_id TEXT PRIMARY KEY,
                    subject_node_id TEXT NOT NULL,
                    capsule_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS node_state (
                    node_id TEXT PRIMARY KEY,
                    sequence INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    state_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS delta_ledger (
                    packet_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    packet_json TEXT NOT NULL,
                    accepted_at TEXT NOT NULL,
                    UNIQUE(node_id, sequence)
                );
                CREATE TABLE IF NOT EXISTS stream_ledger (
                    stream_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    start_sequence INTEGER NOT NULL,
                    end_sequence INTEGER NOT NULL,
                    stream_hash TEXT NOT NULL,
                    accepted_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_ledger (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_retention_checkpoint (
                    checkpoint_id INTEGER PRIMARY KEY CHECK(checkpoint_id = 1),
                    pruned_through_sequence INTEGER NOT NULL,
                    anchor_hash TEXT NOT NULL,
                    pruned_rows INTEGER NOT NULL,
                    checkpoint_json TEXT NOT NULL,
                    checkpoint_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS discovery_runs (
                    run_id TEXT PRIMARY KEY,
                    run_json TEXT NOT NULL,
                    completed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS discovery_observations (
                    observation_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    observation_json TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS device_schemas (
                    schema_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    schema_json TEXT NOT NULL,
                    generated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS action_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS probe_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS webos_pairing_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS webos_integration_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS webos_action_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            db.execute("PRAGMA journal_size_limit=4194304")
        pruned = self.prune_audit_ledger(force=True)
        if pruned and self.path.stat().st_size > 16 * 1024 * 1024:
            # Startup is the only safe point for a full compaction.  Durable
            # pairing, device and preference tables are deliberately untouched.
            with self.connect() as db:
                db.execute("VACUUM")

    def _prune_audit_with_connection(self, db: sqlite3.Connection, *, force: bool) -> int:
        row = db.execute(
            "SELECT COUNT(*) AS total, COALESCE(MAX(sequence), 0) AS head FROM audit_ledger"
        ).fetchone()
        total = int(row["total"])
        head = int(row["head"])
        if total <= self.audit_max_rows:
            return 0
        if not force and head % self.AUDIT_PRUNE_CHECK_INTERVAL:
            return 0
        remove_count = total - self.audit_prune_to_rows
        boundary = db.execute(
            "SELECT sequence,event_hash FROM audit_ledger ORDER BY sequence LIMIT 1 OFFSET ?",
            (remove_count - 1,),
        ).fetchone()
        if boundary is None:
            return 0
        previous = db.execute(
            "SELECT checkpoint_hash,pruned_rows FROM audit_retention_checkpoint WHERE checkpoint_id=1"
        ).fetchone()
        now = utc_now_iso()
        checkpoint = {
            "schema_version": "aion.audit-retention-checkpoint.v1",
            "pruned_through_sequence": int(boundary["sequence"]),
            "anchor_hash": str(boundary["event_hash"]),
            "pruned_rows": int(previous["pruned_rows"]) + remove_count if previous else remove_count,
            "previous_checkpoint_hash": str(previous["checkpoint_hash"]) if previous else "0" * 64,
            "updated_at": now,
        }
        checkpoint_hash = canonical_hash(checkpoint)
        db.execute("DELETE FROM audit_ledger WHERE sequence <= ?", (boundary["sequence"],))
        db.execute(
            "INSERT INTO audit_retention_checkpoint("
            "checkpoint_id,pruned_through_sequence,anchor_hash,pruned_rows,checkpoint_json,checkpoint_hash,updated_at"
            ") VALUES(1,?,?,?,?,?,?) ON CONFLICT(checkpoint_id) DO UPDATE SET "
            "pruned_through_sequence=excluded.pruned_through_sequence,anchor_hash=excluded.anchor_hash,"
            "pruned_rows=excluded.pruned_rows,checkpoint_json=excluded.checkpoint_json,"
            "checkpoint_hash=excluded.checkpoint_hash,updated_at=excluded.updated_at",
            (
                checkpoint["pruned_through_sequence"], checkpoint["anchor_hash"],
                checkpoint["pruned_rows"], canonical_bytes(checkpoint).decode(), checkpoint_hash, now,
            ),
        )
        return remove_count

    def prune_audit_ledger(self, *, force: bool = False) -> int:
        """Bound disposable audit history without touching durable user/device state."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return self._prune_audit_with_connection(db, force=force)

    def append_audit(self, event_type: str, payload: Dict[str, Any]) -> str:
        with self.connect() as db:
            # Serialize the read-head/append pair across voice, phone and
            # supervisor threads.  WAL alone does not make that pair atomic.
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT event_hash FROM audit_ledger ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = row["event_hash"] if row else "0" * 64
            event = {
                "event_type": event_type,
                "payload": payload,
                "previous_hash": previous_hash,
                "created_at": utc_now_iso(),
            }
            event_hash = canonical_hash(event)
            db.execute(
                "INSERT INTO audit_ledger(event_type,event_json,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?)",
                (event_type, canonical_bytes(event).decode(), previous_hash, event_hash, event["created_at"]),
            )
            self._prune_audit_with_connection(db, force=False)
            return event_hash

    def save_node(self, record: NodeRecord) -> None:
        payload = record.to_dict()
        with self.connect() as db:
            db.execute(
                "INSERT INTO nodes(node_id,record_json,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(node_id) DO UPDATE SET record_json=excluded.record_json,updated_at=excluded.updated_at",
                (record.profile.node_id, canonical_bytes(payload).decode(), utc_now_iso()),
            )
        self.append_audit("node_saved", {"node_id": record.profile.node_id, "role": record.role.value, "enrollment": record.enrollment.value})

    def get_node(self, node_id: str) -> NodeRecord | None:
        with self.connect() as db:
            row = db.execute("SELECT record_json FROM nodes WHERE node_id=?", (node_id,)).fetchone()
        if not row:
            return None
        value = json.loads(row["record_json"])
        return NodeRecord(
            profile=DeviceProfile.from_dict(value["profile"]),
            role=NodeRole(value["role"]),
            public_key=value["public_key"],
            enrollment=EnrollmentState(value["enrollment"]),
            mother_id=value.get("mother_id"),
            last_seen_at=value["last_seen_at"],
        )

    def list_nodes(self) -> list[NodeRecord]:
        with self.connect() as db:
            ids = [row["node_id"] for row in db.execute("SELECT node_id FROM nodes ORDER BY node_id")]
        return [record for node_id in ids if (record := self.get_node(node_id)) is not None]

    def save_capsule(self, capsule: CapabilityCapsule) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO capability_capsules(capsule_id,subject_node_id,capsule_json,created_at) VALUES(?,?,?,?)",
                (capsule.capsule_id, capsule.subject_node_id, canonical_bytes(capsule.to_dict()).decode(), utc_now_iso()),
            )
        self.append_audit("capability_capsule_issued", {"capsule_id": capsule.capsule_id, "subject_node_id": capsule.subject_node_id})

    def state_for(self, node_id: str) -> tuple[int, Dict[str, Any], str]:
        with self.connect() as db:
            row = db.execute("SELECT sequence,state_json,state_hash FROM node_state WHERE node_id=?", (node_id,)).fetchone()
        if not row:
            empty: Dict[str, Any] = {}
            return 0, empty, canonical_hash(empty)
        return int(row["sequence"]), json.loads(row["state_json"]), row["state_hash"]

    def accept_delta(self, packet: DeltaPacket, *, public_key: str) -> Dict[str, Any]:
        if not packet.verify(public_key):
            raise ValueError("Delta signature or payload hash is invalid")
        sequence, previous, previous_hash = self.state_for(packet.node_id)
        if packet.sequence != sequence + 1:
            raise ValueError(f"Delta sequence mismatch: expected {sequence + 1}, got {packet.sequence}")
        if packet.base_state_hash != previous_hash:
            raise ValueError("Delta base state does not match the mother ledger")
        current = apply_state_delta(previous, packet.changes)
        if canonical_hash(current) != packet.result_state_hash:
            raise ValueError("Delta result state hash is invalid")
        with self.connect() as db:
            db.execute(
                "INSERT INTO delta_ledger(packet_id,node_id,sequence,packet_json,accepted_at) VALUES(?,?,?,?,?)",
                (packet.packet_id, packet.node_id, packet.sequence, canonical_bytes(packet.to_dict()).decode(), utc_now_iso()),
            )
            db.execute(
                "INSERT INTO node_state(node_id,sequence,state_json,state_hash,updated_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(node_id) DO UPDATE SET sequence=excluded.sequence,state_json=excluded.state_json,state_hash=excluded.state_hash,updated_at=excluded.updated_at",
                (packet.node_id, packet.sequence, canonical_bytes(current).decode(), packet.result_state_hash, utc_now_iso()),
            )
        self.append_audit("delta_accepted", {"packet_id": packet.packet_id, "node_id": packet.node_id, "sequence": packet.sequence})
        return current

    def accept_stream(self, stream: GlyphDeltaStream, *, public_key: str) -> Dict[str, Any]:
        if not stream.verify(public_key):
            raise ValueError("Glyph delta stream signature or payload hash is invalid")
        sequence, previous, previous_hash = self.state_for(stream.node_id)
        if stream.start_sequence != sequence + 1:
            raise ValueError(
                f"Stream sequence mismatch: expected {sequence + 1}, got {stream.start_sequence}"
            )
        states = stream.states()
        if canonical_hash(states[0]) != previous_hash:
            raise ValueError("Glyph delta stream base state does not match the mother ledger")
        final_state = states[-1]
        with self.connect() as db:
            db.execute(
                "INSERT INTO stream_ledger(stream_id,node_id,start_sequence,end_sequence,stream_hash,accepted_at) VALUES(?,?,?,?,?,?)",
                (
                    stream.stream_id,
                    stream.node_id,
                    stream.start_sequence,
                    stream.end_sequence,
                    stream.payload_hash,
                    utc_now_iso(),
                ),
            )
            db.execute(
                "INSERT INTO node_state(node_id,sequence,state_json,state_hash,updated_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(node_id) DO UPDATE SET sequence=excluded.sequence,state_json=excluded.state_json,state_hash=excluded.state_hash,updated_at=excluded.updated_at",
                (
                    stream.node_id,
                    stream.end_sequence,
                    canonical_bytes(final_state).decode(),
                    canonical_hash(final_state),
                    utc_now_iso(),
                ),
            )
        self.append_audit(
            "glyph_stream_accepted",
            {
                "stream_id": stream.stream_id,
                "node_id": stream.node_id,
                "start_sequence": stream.start_sequence,
                "end_sequence": stream.end_sequence,
            },
        )
        return final_state

    def counts(self) -> Dict[str, int]:
        with self.connect() as db:
            return {
                table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in (
                    "nodes",
                    "capability_capsules",
                    "delta_ledger",
                    "stream_ledger",
                    "audit_ledger",
                    "discovery_observations",
                    "device_schemas",
                    "action_proposals",
                    "probe_receipts",
                    "webos_pairing_receipts",
                    "webos_integration_receipts",
                    "webos_action_receipts",
                )
            }

    def save_discovery_run(self, run: DiscoveryRun) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO discovery_runs(run_id,run_json,completed_at) VALUES(?,?,?)",
                (run.run_id, canonical_bytes(run.to_dict()).decode(), run.completed_at),
            )
            for observation in run.observations:
                db.execute(
                    "INSERT INTO discovery_observations(observation_id,source,observation_json,last_seen_at) VALUES(?,?,?,?) "
                    "ON CONFLICT(observation_id) DO UPDATE SET source=excluded.source,observation_json=excluded.observation_json,last_seen_at=excluded.last_seen_at",
                    (
                        observation.observation_id,
                        observation.source,
                        canonical_bytes(observation.to_dict()).decode(),
                        observation.observed_at,
                    ),
                )
        self.append_audit(
            "discovery_completed",
            {"run_id": run.run_id, "observations": len(run.observations), "errors": run.errors},
        )

    def list_observations(self) -> list[DiscoveryObservation]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT observation_json FROM discovery_observations ORDER BY last_seen_at DESC, observation_id"
            ).fetchall()
        return [DiscoveryObservation(**json.loads(row["observation_json"])) for row in rows]

    def save_schema(self, schema: DeviceSchema) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO device_schemas(schema_id,node_id,schema_json,generated_at) VALUES(?,?,?,?)",
                (schema.schema_id, schema.node_id, canonical_bytes(schema.to_dict()).decode(), schema.generated_at),
            )
        self.append_audit(
            "device_schema_generated",
            {
                "schema_id": schema.schema_id,
                "node_id": schema.node_id,
                "controls": len(schema.controls),
                "documents": len(schema.documentation),
            },
        )

    @staticmethod
    def _schema_from_dict(value: Dict[str, Any]) -> DeviceSchema:
        controls = []
        for item in value.get("controls", []):
            data = dict(item)
            from .contracts import RiskLevel

            data["risk"] = RiskLevel(data["risk"])
            controls.append(ControlSurface(**data))
        documentation = [DocumentationArtifact(**item) for item in value.get("documentation", [])]
        data = dict(value)
        data["controls"] = controls
        data["documentation"] = documentation
        return DeviceSchema(**data)

    def get_schema_for_node(self, node_id: str) -> DeviceSchema | None:
        with self.connect() as db:
            rows = db.execute(
                "SELECT schema_json FROM device_schemas WHERE node_id=?",
                (node_id,),
            ).fetchall()
        schemas = [self._schema_from_dict(json.loads(row["schema_json"])) for row in rows]
        if not schemas:
            return None
        return max(
            schemas,
            key=lambda item: (
                len(item.controls),
                len(item.documentation),
                item.confidence,
                item.generated_at,
            ),
        )

    def list_schemas(self) -> list[DeviceSchema]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT schema_json FROM device_schemas ORDER BY generated_at DESC, schema_id"
            ).fetchall()
        return [self._schema_from_dict(json.loads(row["schema_json"])) for row in rows]

    def save_action_proposal(self, proposal: FieldActionProposal) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO action_proposals(proposal_id,node_id,proposal_json,created_at) VALUES(?,?,?,?)",
                (
                    proposal.proposal_id,
                    proposal.node_id,
                    canonical_bytes(proposal.to_dict()).decode(),
                    proposal.created_at,
                ),
            )
        self.append_audit(
            "field_action_proposed",
            {"proposal_id": proposal.proposal_id, "node_id": proposal.node_id, "state": proposal.state},
        )

    def latest_capsule_for_node(self, node_id: str) -> CapabilityCapsule | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT capsule_json FROM capability_capsules WHERE subject_node_id=? ORDER BY created_at DESC LIMIT 1",
                (node_id,),
            ).fetchone()
        return CapabilityCapsule(**json.loads(row["capsule_json"])) if row else None

    def save_probe_receipt(self, receipt: ReadOnlyProbeReceipt) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO probe_receipts(receipt_id,node_id,receipt_json,created_at) VALUES(?,?,?,?)",
                (
                    receipt.receipt_id,
                    receipt.node_id,
                    canonical_bytes(receipt.to_dict()).decode(),
                    receipt.created_at,
                ),
            )
        self.append_audit(
            "read_only_probe_completed",
            {
                "receipt_id": receipt.receipt_id,
                "node_id": receipt.node_id,
                "action_id": receipt.action_id,
                "response_status": receipt.response_status,
            },
        )

    def save_webos_pairing_receipt(self, receipt: WebOsPairingReceipt) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO webos_pairing_receipts(receipt_id,node_id,receipt_json,created_at) VALUES(?,?,?,?)",
                (
                    receipt.receipt_id,
                    receipt.node_id,
                    canonical_bytes(receipt.to_dict()).decode(),
                    receipt.created_at,
                ),
            )
        self.append_audit(
            "webos_read_only_pairing_completed",
            {
                "receipt_id": receipt.receipt_id,
                "node_id": receipt.node_id,
                "host": receipt.host,
                "proof_action": receipt.proof_action,
            },
        )

    def save_webos_integration_receipt(self, receipt: WebOsIntegrationReceipt) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO webos_integration_receipts(receipt_id,node_id,receipt_json,created_at) VALUES(?,?,?,?)",
                (
                    receipt.receipt_id,
                    receipt.node_id,
                    canonical_bytes(receipt.to_dict()).decode(),
                    receipt.created_at,
                ),
            )
        self.append_audit(
            "webos_integration_completed",
            {
                "receipt_id": receipt.receipt_id,
                "node_id": receipt.node_id,
                "connected_surfaces": receipt.connected_surfaces,
                "volume_round_trip": receipt.volume_round_trip,
            },
        )

    def latest_webos_integration_receipt(self, node_id: str) -> WebOsIntegrationReceipt | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT receipt_json FROM webos_integration_receipts WHERE node_id=? ORDER BY created_at DESC LIMIT 1",
                (node_id,),
            ).fetchone()
        return WebOsIntegrationReceipt(**json.loads(row["receipt_json"])) if row else None

    def save_webos_action_receipt(self, receipt: WebOsActionReceipt, *, source: str) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO webos_action_receipts(receipt_id,node_id,receipt_json,created_at) VALUES(?,?,?,?)",
                (
                    receipt.receipt_id,
                    receipt.node_id,
                    canonical_bytes(receipt.to_dict()).decode(),
                    receipt.created_at,
                ),
            )
        self.append_audit(
            "webos_action_verified",
            {
                "receipt_id": receipt.receipt_id,
                "node_id": receipt.node_id,
                "action": receipt.action,
                "source": source,
                "verified": receipt.verified,
                "before": receipt.before,
                "after": receipt.after,
            },
        )

    def verify_audit_chain(self) -> bool:
        with self.connect() as db:
            checkpoint_row = db.execute(
                "SELECT checkpoint_json,checkpoint_hash,anchor_hash,pruned_through_sequence "
                "FROM audit_retention_checkpoint WHERE checkpoint_id=1"
            ).fetchone()
            rows = db.execute(
                "SELECT sequence,event_json,previous_hash,event_hash FROM audit_ledger ORDER BY sequence"
            ).fetchall()
        previous_hash = "0" * 64
        pruned_through = 0
        if checkpoint_row:
            checkpoint = json.loads(checkpoint_row["checkpoint_json"])
            if canonical_hash(checkpoint) != checkpoint_row["checkpoint_hash"]:
                return False
            if checkpoint.get("anchor_hash") != checkpoint_row["anchor_hash"]:
                return False
            if int(checkpoint.get("pruned_through_sequence", -1)) != int(checkpoint_row["pruned_through_sequence"]):
                return False
            previous_hash = str(checkpoint_row["anchor_hash"])
            pruned_through = int(checkpoint_row["pruned_through_sequence"])
        if rows and int(rows[0]["sequence"]) != pruned_through + 1:
            return False
        for row in rows:
            event = json.loads(row["event_json"])
            if row["previous_hash"] != previous_hash:
                return False
            if event.get("previous_hash") != previous_hash:
                return False
            if canonical_hash(event) != row["event_hash"]:
                return False
            previous_hash = row["event_hash"]
        return True
