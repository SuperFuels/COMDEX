"""Durable, fail-closed recovery state for GlyphChain network partitions.

The store intentionally records only aggregate recovery facts and digests of
peer identities.  A conflicting trusted finality view is sticky: ordinary
network observations cannot clear the halt.  A signed desktop administrator
must acknowledge the exact halt identifier before consensus may resume.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "glyphchain.partition-recovery.v1"
PHASE_HEALTHY = "HEALTHY"
PHASE_PARTITION_SUSPECTED = "PARTITION_SUSPECTED"
PHASE_REJOIN_ASSESSING = "REJOIN_ASSESSING"
PHASE_BLOCK_CATCHUP = "BLOCK_CATCHUP"
PHASE_SNAPSHOT_REQUIRED = "SNAPSHOT_REQUIRED"
PHASE_SAFETY_HALT = "SAFETY_HALT"
PHASES = {
    PHASE_HEALTHY,
    PHASE_PARTITION_SUSPECTED,
    PHASE_REJOIN_ASSESSING,
    PHASE_BLOCK_CATCHUP,
    PHASE_SNAPSHOT_REQUIRED,
    PHASE_SAFETY_HALT,
}


class PartitionRecoveryError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    payload = value if isinstance(value, bytes) else _canonical(value)
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def peer_digest(value: str) -> str:
    return _sha256(str(value or "").encode("utf-8"))


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def recovery_root_from_env() -> Path:
    configured = str(os.getenv("GLYPHCHAIN_PARTITION_RECOVERY_DIR", "") or "").strip()
    if configured:
        return Path(configured).expanduser()
    state_root = Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state"))
    return state_root / "partition-recovery"


def classify_validated_views(
    views: Iterable[dict[str, Any]],
    *,
    local_height: int,
    local_block_id: str = "",
) -> dict[str, Any]:
    """Classify already cryptographically validated peer finality views.

    Trust is established before this function is called.  Peer count is not a
    substitute for trust and is used only as an observation count.
    """
    normalized: list[dict[str, Any]] = []
    by_height: dict[int, set[str]] = {}
    for raw in views:
        height = _integer(raw.get("height"), -1)
        block_id = str(raw.get("block_id") or "").strip()
        if height <= 0 or not block_id:
            continue
        item = {
            "height": height,
            "round": max(0, _integer(raw.get("round"), 0)),
            "block_id": block_id,
            "source_digest": str(raw.get("source_digest") or ""),
            "payload_index": _integer(raw.get("payload_index"), -1),
        }
        normalized.append(item)
        by_height.setdefault(height, set()).add(block_id)

    conflicts = [
        {"height": height, "block_ids": sorted(block_ids)}
        for height, block_ids in sorted(by_height.items())
        if len(block_ids) > 1
    ]
    local_block = str(local_block_id or "").strip()
    if local_height > 0 and local_block:
        peer_blocks = by_height.get(int(local_height), set())
        if any(value != local_block for value in peer_blocks):
            conflicts.append({
                "height": int(local_height),
                "block_ids": sorted(peer_blocks | {local_block}),
            })

    if conflicts:
        conflict_digest = _sha256(conflicts)
        return {
            "phase": PHASE_SAFETY_HALT,
            "reason": "conflicting_trusted_finality_views",
            "conflict_digest": conflict_digest,
            "conflicting_heights": sorted({int(item["height"]) for item in conflicts}),
            "candidate": None,
            "valid_view_count": len(normalized),
        }

    ahead = [item for item in normalized if int(item["height"]) > int(local_height)]
    candidate = max(ahead, key=lambda item: (int(item["height"]), int(item["round"])), default=None)
    return {
        "phase": PHASE_BLOCK_CATCHUP if candidate else PHASE_HEALTHY,
        "reason": "trusted_higher_finality_available" if candidate else "no_higher_trusted_finality",
        "conflict_digest": "",
        "conflicting_heights": [],
        "candidate": candidate,
        "valid_view_count": len(normalized),
    }


class PartitionRecoveryStore:
    """Atomic state plus a bounded hash-chained transition journal."""

    MAX_JOURNAL_BYTES = 256 * 1024 * 1024

    def __init__(
        self,
        root: Path,
        *,
        chain_id: str,
        node_id: str,
        clock_ms: Any | None = None,
        max_events: int | None = None,
    ) -> None:
        self.root = Path(root)
        self.state_path = self.root / "partition-recovery.json"
        self.journal_path = self.root / "partition-recovery-events.jsonl"
        self.chain_id = str(chain_id or "").strip()
        self.node_id = str(node_id or "").strip()
        if not self.chain_id or not self.node_id:
            raise PartitionRecoveryError("partition recovery requires chain_id and node_id")
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        configured_limit = _integer(os.getenv("GLYPHCHAIN_PARTITION_EVENT_LIMIT", "4096"), 4096)
        self.max_events = max(32, min(100_000, int(max_events or configured_limit)))

    @classmethod
    def from_env(cls, *, chain_id: str, node_id: str) -> "PartitionRecoveryStore":
        return cls(recovery_root_from_env(), chain_id=chain_id, node_id=node_id)

    def _default(self) -> dict[str, Any]:
        now = int(self._clock_ms())
        return {
            "schema_version": SCHEMA_VERSION,
            "chain_id": self.chain_id,
            "node_id": self.node_id,
            "phase": PHASE_HEALTHY,
            "halt_id": "",
            "reason": "initial_state",
            "detected_at_ms": None,
            "last_healthy_at_ms": now,
            "updated_at_ms": now,
            "local_finalized_height": 0,
            "target_finalized_height": 0,
            "target_block_id": "",
            "target_round": 0,
            "source_peer_digest": "",
            "valid_view_count": 0,
            "missing_from_height": None,
            "missing_to_height": None,
            "recovery_attempts": 0,
            "last_error": "",
            "event_sequence": 0,
            "last_event_hash": "",
        }

    def status(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._default()
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PartitionRecoveryError("partition recovery state unreadable") from exc
        if not isinstance(value, dict):
            raise PartitionRecoveryError("partition recovery state invalid")
        state_hash = str(value.pop("state_hash", "") or "")
        if state_hash != _sha256(value):
            raise PartitionRecoveryError("partition recovery state hash mismatch")
        if value.get("schema_version") != SCHEMA_VERSION:
            raise PartitionRecoveryError("partition recovery schema unsupported")
        if value.get("chain_id") != self.chain_id or value.get("node_id") != self.node_id:
            raise PartitionRecoveryError("partition recovery identity mismatch")
        if value.get("phase") not in PHASES:
            raise PartitionRecoveryError("partition recovery phase invalid")
        return value

    def is_halted(self) -> bool:
        return self.status().get("phase") == PHASE_SAFETY_HALT

    def _journal(self) -> list[dict[str, Any]]:
        if not self.journal_path.exists():
            return []
        if self.journal_path.stat().st_size > self.MAX_JOURNAL_BYTES:
            raise PartitionRecoveryError("partition recovery journal exceeds its size limit")
        records: list[dict[str, Any]] = []
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PartitionRecoveryError("partition recovery journal invalid") from exc
            if not isinstance(item, dict):
                raise PartitionRecoveryError("partition recovery journal invalid")
            records.append(item)
        return records

    def verify_journal(self) -> bool:
        records = self._journal()
        if len(records) > self.max_events:
            return False
        previous = str(records[0].get("previous_event_hash") or "") if records else ""
        for record in records:
            claimed = str(record.get("event_hash") or "")
            body = dict(record)
            body.pop("event_hash", None)
            if str(body.get("previous_event_hash") or "") != previous:
                return False
            if claimed != _sha256(body):
                return False
            previous = claimed
        return True

    def transition(self, phase: str, *, reason: str, **fields: Any) -> dict[str, Any]:
        wanted = str(phase or "").strip().upper()
        if wanted not in PHASES:
            raise PartitionRecoveryError("partition recovery phase invalid")
        current = self.status()
        if current.get("phase") == PHASE_SAFETY_HALT and wanted != PHASE_SAFETY_HALT:
            raise PartitionRecoveryError("partition recovery safety halt requires explicit administrator clearance")
        return self._write_transition(current, wanted, reason=reason, fields=fields)

    def clear_safety_halt(
        self,
        *,
        halt_id: str,
        operator_id: str,
        reason: str,
        confirmation: str,
    ) -> dict[str, Any]:
        current = self.status()
        if current.get("phase") != PHASE_SAFETY_HALT:
            raise PartitionRecoveryError("partition recovery is not safety halted")
        if confirmation != "CLEAR GLYPHCHAIN PARTITION SAFETY HALT":
            raise PartitionRecoveryError("partition recovery clearance confirmation required")
        if not halt_id or halt_id != str(current.get("halt_id") or ""):
            raise PartitionRecoveryError("partition recovery halt identifier mismatch")
        if not str(operator_id or "").strip() or not str(reason or "").strip():
            raise PartitionRecoveryError("partition recovery clearance requires operator and reason")
        return self._write_transition(current, PHASE_REJOIN_ASSESSING, reason="administrator_clearance", fields={
            "halt_id": "",
            "last_error": "",
            "cleared_by": str(operator_id).strip(),
            "clearance_reason": str(reason).strip()[:1000],
            "detected_at_ms": current.get("detected_at_ms"),
        }, allow_halt_clear=True)

    def _write_transition(
        self,
        current: dict[str, Any],
        phase: str,
        *,
        reason: str,
        fields: dict[str, Any],
        allow_halt_clear: bool = False,
    ) -> dict[str, Any]:
        if current.get("phase") == PHASE_SAFETY_HALT and phase != PHASE_SAFETY_HALT and not allow_halt_clear:
            raise PartitionRecoveryError("partition recovery safety halt requires explicit administrator clearance")
        now = int(self._clock_ms())
        next_state = dict(current)
        next_state.update({key: value for key, value in fields.items() if key != "state_hash"})
        next_state.update({
            "schema_version": SCHEMA_VERSION,
            "chain_id": self.chain_id,
            "node_id": self.node_id,
            "phase": phase,
            "reason": str(reason or "").strip()[:500],
            "updated_at_ms": now,
        })
        if phase == PHASE_HEALTHY:
            next_state.update({
                "halt_id": "",
                "detected_at_ms": None,
                "last_healthy_at_ms": now,
                "target_finalized_height": 0,
                "target_block_id": "",
                "target_round": 0,
                "source_peer_digest": "",
                "missing_from_height": None,
                "missing_to_height": None,
                "recovery_attempts": 0,
                "last_error": "",
            })
        elif next_state.get("detected_at_ms") is None:
            next_state["detected_at_ms"] = now
        if phase == PHASE_SAFETY_HALT and not str(next_state.get("halt_id") or ""):
            next_state["halt_id"] = _sha256({
                "chain_id": self.chain_id,
                "node_id": self.node_id,
                "reason": next_state["reason"],
                "conflict_digest": next_state.get("conflict_digest"),
                "detected_at_ms": next_state.get("detected_at_ms"),
            })

        sequence = _integer(current.get("event_sequence"), 0) + 1
        previous_hash = str(current.get("last_event_hash") or "")
        event = {
            "schema_version": SCHEMA_VERSION,
            "sequence": sequence,
            "recorded_at_ms": now,
            "chain_id": self.chain_id,
            "node_id": self.node_id,
            "from_phase": str(current.get("phase") or PHASE_HEALTHY),
            "to_phase": phase,
            "reason": next_state["reason"],
            "local_finalized_height": _integer(next_state.get("local_finalized_height"), 0),
            "target_finalized_height": _integer(next_state.get("target_finalized_height"), 0),
            "target_block_id": str(next_state.get("target_block_id") or ""),
            "halt_id": str(next_state.get("halt_id") or ""),
            "previous_event_hash": previous_hash,
        }
        event["event_hash"] = _sha256(event)
        next_state["event_sequence"] = sequence
        next_state["last_event_hash"] = event["event_hash"]

        self.root.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass
        records = self._journal()
        records.append(event)
        records = records[-self.max_events:]
        journal_tmp = self.journal_path.with_suffix(".jsonl.tmp")
        with journal_tmp.open("w", encoding="utf-8") as handle:
            for item in records:
                handle.write(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(journal_tmp, self.journal_path)
        try:
            os.chmod(self.journal_path, 0o600)
        except OSError:
            pass

        persisted = dict(next_state)
        persisted["state_hash"] = _sha256(persisted)
        state_tmp = self.state_path.with_suffix(".json.tmp")
        with state_tmp.open("w", encoding="utf-8") as handle:
            json.dump(persisted, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(state_tmp, self.state_path)
        try:
            os.chmod(self.state_path, 0o600)
        except OSError:
            pass
        return dict(next_state)
