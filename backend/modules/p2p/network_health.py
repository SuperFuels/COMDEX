"""Privacy-safe local health snapshots for GlyphChain operators.

The monitor deliberately stores aggregates only.  It never records peer URLs,
IP addresses, node identifiers, validator identifiers, transactions, document
hashes, signatures, or Legal workspace data.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "glyphchain.network-health.v1"


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _threshold(name: str, default: int, *, minimum: int = 1) -> int:
    return max(minimum, _integer(os.getenv(name, default), default))


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _peer_aggregates(peers: Iterable[Any], *, now_ms: float) -> dict[str, int]:
    result = {
        "total": 0,
        "verified": 0,
        "stale": 0,
        "banned": 0,
        "validators": 0,
        "verified_validators": 0,
        "relays": 0,
    }
    stale_after = _threshold("GLYPHCHAIN_PEER_STALE_AFTER_MS", 5 * 60 * 1000)
    for peer in peers:
        result["total"] += 1
        role = str(getattr(peer, "role", "") or "").strip().lower()
        verified = bool(getattr(peer, "hello_ok", False))
        banned = bool(getattr(peer, "banned", False))
        seen = _number(getattr(peer, "last_seen_ms", None)) or _number(getattr(peer, "last_hello_ms", None)) or 0.0
        if verified:
            result["verified"] += 1
        if banned:
            result["banned"] += 1
        if seen <= 0 or now_ms - seen > stale_after:
            result["stale"] += 1
        if role == "validator":
            result["validators"] += 1
            if verified and not banned:
                result["verified_validators"] += 1
        elif role == "relay":
            result["relays"] += 1
    return result


def _fork_signal(recent_qcs: Any) -> tuple[bool, int]:
    by_height: dict[int, set[str]] = {}
    if not isinstance(recent_qcs, list):
        return False, 0
    for qc in recent_qcs[-128:]:
        if not isinstance(qc, dict):
            continue
        height = _integer(qc.get("height"), -1)
        block_id = str(qc.get("block_id") or "").strip()
        if height >= 0 and block_id:
            by_height.setdefault(height, set()).add(block_id)
    conflicts = sum(1 for values in by_height.values() if len(values) > 1)
    return conflicts > 0, conflicts


def _ingress_aggregates(snapshot: Any) -> dict[str, int]:
    totals = {"queue_length": 0, "queue_capacity": 0, "processed": 0, "dropped_full": 0, "dropped_duplicate": 0}
    lanes = snapshot.get("lanes", {}) if isinstance(snapshot, dict) else {}
    if not isinstance(lanes, dict):
        return totals
    for value in lanes.values():
        if not isinstance(value, dict):
            continue
        counters = value.get("counters", {}) if isinstance(value.get("counters"), dict) else {}
        totals["queue_length"] += _integer(value.get("queue_len"))
        totals["queue_capacity"] += _integer(value.get("queue_max"))
        totals["processed"] += _integer(counters.get("processed"))
        totals["dropped_full"] += _integer(counters.get("dropped_full"))
        totals["dropped_duplicate"] += _integer(counters.get("dropped_dup"))
    return totals


def build_health_snapshot(
    *,
    consensus: dict[str, Any],
    peers: Iterable[Any],
    peer_limit: int,
    ingress: dict[str, Any] | None,
    ledger_storage: dict[str, Any] | None = None,
    previous: dict[str, Any] | None = None,
    now_ms: float | None = None,
) -> dict[str, Any]:
    """Create an aggregate snapshot and deterministic operator alerts."""
    now = float(now_ms if now_ms is not None else time.time() * 1000.0)
    finalized = _integer(consensus.get("finalized_height"))
    height = _integer(consensus.get("height") or consensus.get("next_height"))
    round_number = _integer(consensus.get("round"))
    last_qc = consensus.get("last_qc") if isinstance(consensus.get("last_qc"), dict) else {}
    last_finality_ms = _number(last_qc.get("ts_ms"))
    finality_age_ms = max(0, int(now - last_finality_ms)) if last_finality_ms else None
    peers_summary = _peer_aggregates(peers, now_ms=now)
    ingress_summary = _ingress_aggregates(ingress)
    ledger_summary = dict(ledger_storage or {})
    fork_detected, conflicting_heights = _fork_signal(consensus.get("recent_qcs"))
    finality = consensus.get("quorum_finality") if isinstance(consensus.get("quorum_finality"), dict) else {}
    partition_recovery = consensus.get("partition_recovery") if isinstance(consensus.get("partition_recovery"), dict) else {}
    protocol_upgrade = consensus.get("protocol_upgrade") if isinstance(consensus.get("protocol_upgrade"), dict) else {}
    participation = consensus.get("network_participation") if isinstance(consensus.get("network_participation"), dict) else {}
    role = str(participation.get("role") or "light").strip().lower()

    previous_ingress = previous.get("ingress", {}) if isinstance(previous, dict) else {}
    dropped_since_previous = max(
        0,
        ingress_summary["dropped_full"] - _integer(previous_ingress.get("dropped_full")),
    )
    alerts: list[dict[str, str]] = []

    def alert(code: str, severity: str, message: str) -> None:
        alerts.append({"code": code, "severity": severity, "message": message})

    if fork_detected:
        alert("conflicting_finality_history", "critical", "Conflicting finalized block identifiers were observed at the same height.")
    if height > finalized + _threshold("GLYPHCHAIN_HEIGHT_LAG_ALERT", 4, minimum=0):
        alert("finality_height_lag", "warning", "The local consensus height is ahead of the finalized height beyond the configured limit.")
    if round_number >= _threshold("GLYPHCHAIN_ROUND_ALERT", 4, minimum=1):
        alert("extended_consensus_round", "warning", "Consensus has advanced through an unusual number of rounds without finalizing.")
    stale_finality = _threshold("GLYPHCHAIN_FINALITY_STALE_AFTER_MS", 10 * 60 * 1000)
    if finalized > 0 and finality_age_ms is not None and finality_age_ms > stale_finality:
        alert("finality_stale", "warning", "No new finality certificate has been observed within the configured interval.")
    if peer_limit > 0 and peers_summary["total"] >= max(1, int(peer_limit * 0.9)):
        alert("peer_store_near_capacity", "warning", "The bounded peer registry is at least 90 percent full.")
    if role in {"relay", "validator"} and peers_summary["verified"] == 0:
        alert("no_verified_peers", "critical", "This elevated node has no verified peer connection.")
    if dropped_since_previous > 0:
        alert("ingress_capacity_drop", "warning", "The node dropped new messages because a bounded ingress queue was full.")
    if bool(ledger_summary.get("at_capacity")):
        alert("ledger_storage_capacity_reached", "critical", "The bounded ledger has reached its approved local storage limit.")
    elif bool(ledger_summary.get("near_capacity")):
        alert("ledger_storage_near_capacity", "warning", "The bounded ledger is at least 90 percent full.")
    if bool(finality.get("enabled")) and not bool(finality.get("latest_certificate")) and finalized > 0:
        alert("portable_finality_certificate_missing", "critical", "The latest finalized state has no portable quorum-finality certificate.")
    if finality.get("configuration_error"):
        alert("finality_configuration_error", "critical", "The quorum-finality trust configuration is invalid.")
    recovery_phase = str(partition_recovery.get("phase") or "HEALTHY").strip().upper()
    if recovery_phase == "SAFETY_HALT":
        alert("partition_recovery_safety_halt", "critical", "Consensus is halted because trusted finalized histories conflict or recovery state is invalid.")
    elif recovery_phase == "SNAPSHOT_REQUIRED":
        alert("partition_recovery_snapshot_required", "warning", "The partition gap exceeds bounded block catch-up and requires a verified snapshot.")
    elif recovery_phase in {"PARTITION_SUSPECTED", "REJOIN_ASSESSING", "BLOCK_CATCHUP"}:
        alert("partition_recovery_active", "warning", "The node is assessing or recovering from a network partition.")
    upgrade_phase = str(protocol_upgrade.get("phase") or "STABLE").strip().upper()
    if upgrade_phase == "UPGRADE_HALT":
        alert("protocol_upgrade_halt", "critical", "Consensus is halted at an activation boundary because the local release or validator quorum is not ready.")
    elif upgrade_phase == "SCHEDULED" and protocol_upgrade.get("ready_power", 0) < protocol_upgrade.get("quorum_power", 0):
        alert("protocol_upgrade_quorum_not_ready", "warning", "A protocol upgrade is scheduled but the signed validator readiness advertisements have not reached quorum power.")

    severity_order = {"critical": 2, "warning": 1}
    highest = max((severity_order.get(item["severity"], 0) for item in alerts), default=0)
    status = "critical" if highest == 2 else "warning" if highest == 1 else "healthy"
    return {
        "schema_version": SCHEMA_VERSION,
        "recorded_at_ms": int(now),
        "network_digest": _digest(str(consensus.get("chain_id") or "")),
        "privacy_boundary": "aggregate_only_no_peer_addresses_node_ids_transactions_documents_or_signatures",
        "status": status,
        "role": role,
        "consensus": {
            "finalized_height": finalized,
            "height": height,
            "round": round_number,
            "height_lag": max(0, height - (finalized + 1)) if height else 0,
            "last_finality_age_ms": finality_age_ms,
            "finality_latency_ms_last": _number(consensus.get("finality_latency_ms_last")),
            "finality_latency_ms_p50": _number(consensus.get("finality_latency_ms_p50")),
            "finality_latency_ms_p95": _number(consensus.get("finality_latency_ms_p95")),
            "finality_latency_samples": _integer(consensus.get("finality_latency_ms_samples")),
            "fork_signal": fork_detected,
            "conflicting_finalized_heights": conflicting_heights,
            "portable_finality_enabled": bool(finality.get("enabled")),
            "portable_certificate_present": bool(finality.get("latest_certificate")),
        },
        "peers": {**peers_summary, "limit": max(0, int(peer_limit))},
        "ingress": {**ingress_summary, "dropped_full_since_previous": dropped_since_previous},
        "ledger_storage": {
            key: ledger_summary.get(key)
            for key in ("persistence_enabled", "max_bytes", "used_bytes", "remaining_bytes",
                        "utilization_percent", "near_capacity", "at_capacity", "policy")
            if key in ledger_summary
        },
        "partition_recovery": {
            "phase": recovery_phase,
            "local_finalized_height": _integer(partition_recovery.get("local_finalized_height")),
            "target_finalized_height": _integer(partition_recovery.get("target_finalized_height")),
            "recovery_attempts": _integer(partition_recovery.get("recovery_attempts")),
            "state_readable": bool(partition_recovery.get("state_readable", True)),
            "journal_valid": bool(partition_recovery.get("journal_valid", True)),
        },
        "protocol_upgrade": {
            "phase": upgrade_phase,
            "active_version": _integer(protocol_upgrade.get("active_version")),
            "ready_power": _integer(protocol_upgrade.get("ready_power")),
            "quorum_power": _integer(protocol_upgrade.get("quorum_power")),
            "mismatched_validator_count": _integer(protocol_upgrade.get("mismatched_validator_count")),
            "state_readable": bool(protocol_upgrade.get("state_readable", True)),
            "journal_valid": bool(protocol_upgrade.get("journal_valid", True)),
        },
        "alerts": alerts,
    }


class NetworkHealthStore:
    """Bounded, local, hash-chained history of aggregate health snapshots."""

    MAX_FILE_BYTES = 256 * 1024 * 1024

    def __init__(self, root: Path, *, max_records: int | None = None) -> None:
        self.root = Path(root)
        self.path = self.root / "network-health.jsonl"
        self.max_records = max(8, min(100_000, max_records or _threshold("GLYPHCHAIN_HEALTH_HISTORY_LIMIT", 2048, minimum=8)))

    def history(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        if self.path.stat().st_size > self.MAX_FILE_BYTES:
            raise ValueError("network health history exceeds its size limit")
        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return records[-max(1, min(self.max_records, int(limit))):]

    def append(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        records = self.history(limit=self.max_records)
        previous_hash = str(records[-1].get("record_hash") or "") if records else ""
        body = dict(snapshot)
        body.pop("record_hash", None)
        body["previous_record_hash"] = previous_hash
        body["record_hash"] = _digest(_canonical(body).decode("utf-8"))
        records.append(body)
        records = records[-self.max_records:]
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text("".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records), encoding="utf-8")
        os.replace(temporary, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        return body

    def verify(self) -> bool:
        if not self.path.exists():
            return True
        if self.path.stat().st_size > self.MAX_FILE_BYTES:
            return False
        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                return False
            if not isinstance(value, dict):
                return False
            records.append(value)
        if len(records) > self.max_records:
            return False
        previous = str(records[0].get("previous_record_hash") or "") if records else ""
        for record in records:
            claimed = str(record.get("record_hash") or "")
            body = dict(record)
            body.pop("record_hash", None)
            if str(body.get("previous_record_hash") or "") != previous:
                return False
            if claimed != _digest(_canonical(body).decode("utf-8")):
                return False
            previous = claimed
        return True
