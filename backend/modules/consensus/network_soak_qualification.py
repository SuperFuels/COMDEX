"""Bounded local soak qualification for GlyphChain durable network controls."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
from time import monotonic
from typing import Any, Mapping

from backend.modules.consensus.partition_recovery import (
    PHASE_BLOCK_CATCHUP,
    PHASE_HEALTHY,
    PHASE_SAFETY_HALT,
    PartitionRecoveryStore,
)
from backend.modules.p2p.nat_relay import NATRelayError, NATRelayLimits, NATRelayStore


class NetworkSoakQualificationError(ValueError):
    pass


SCHEMA_VERSION = "glyphchain.network-soak-qualification.v1"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class NetworkSoakQualification:
    """Exercise restart, intermittent delivery, partition recovery and isolation."""

    def __init__(self, root: str | Path, *, clock_ms: Any | None = None) -> None:
        self.root = Path(root)
        self.clock_ms = clock_ms or (lambda: int(datetime.now(timezone.utc).timestamp() * 1000))

    def run(
        self,
        *,
        network_count: int = 3,
        cycles_per_network: int = 256,
        restart_interval: int = 16,
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        networks = int(network_count)
        cycles = int(cycles_per_network)
        interval = int(restart_interval)
        if not 2 <= networks <= 8:
            raise NetworkSoakQualificationError("network count must be between 2 and 8")
        if not 8 <= cycles <= 5_000:
            raise NetworkSoakQualificationError("cycles per network must be between 8 and 5000")
        if not 1 <= interval <= cycles:
            raise NetworkSoakQualificationError("restart interval is invalid")
        self._prepare_root()
        started = monotonic()
        results = [self._run_network(index, cycles=cycles, restart_interval=interval) for index in range(networks)]
        isolation = self._cross_network_isolation(networks)
        elapsed = max(0.0, monotonic() - started)
        checks = {
            "all_messages_acknowledged": all(item["messages_acknowledged"] == cycles for item in results),
            "all_duplicates_idempotent": all(item["duplicate_puts_idempotent"] == cycles for item in results),
            "all_delayed_redeliveries_observed": all(item["redeliveries_observed"] == cycles for item in results),
            "all_planned_restarts_recovered": all(item["restart_failures"] == 0 for item in results),
            "all_partition_journals_valid": all(item["partition_journal_valid"] for item in results),
            "all_partition_cycles_returned_healthy": all(item["final_partition_phase"] == PHASE_HEALTHY for item in results),
            "multi_network_cross_chain_rejected": isolation,
            "legal_content_absent": all(item["legal_content_present"] is False for item in results),
        }
        passed = all(checks.values())
        report: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "result": "LOCAL_BOUNDED_SOAK_PASSED" if passed else "FAILED",
            "content_free": True,
            "claim_boundary": (
                "This is a bounded control-plane soak on one local machine. It is not a production "
                "throughput, latency, internet availability, multi-host or denial-of-service result."
            ),
            "configuration": {
                "network_count": networks,
                "cycles_per_network": cycles,
                "total_message_cycles": networks * cycles,
                "restart_interval": interval,
            },
            "checks": checks,
            "networks": results,
            "observed_duration_seconds": round(elapsed, 6),
            "production_ready": False,
            "remaining_external_gates": [
                "sustained representative production load",
                "independent multi-host restarts",
                "real intermittent networks and relay outages",
                "multiple independently operated networks",
                "independent application and consensus security reviews",
            ],
        }
        report["report_sha256"] = sha256(_canonical(report)).hexdigest()
        if not passed:
            raise NetworkSoakQualificationError("bounded network soak failed")
        return report

    def _run_network(self, index: int, *, cycles: int, restart_interval: int) -> dict[str, Any]:
        chain_id = f"glyphchain-soak-{index + 1}"
        network_root = self.root / f"network-{index + 1}"
        limits = NATRelayLimits(
            maximum_messages=32, maximum_per_target=16,
            maximum_message_bytes=4096, maximum_ttl_ms=120_000, pull_batch=16,
        )
        relay = NATRelayStore(network_root / "relay", chain_id=chain_id, limits=limits, clock_ms=self.clock_ms)
        recovery = PartitionRecoveryStore(
            network_root / "partition", chain_id=chain_id, node_id=f"intermittent-{index + 1}",
            clock_ms=self.clock_ms, max_events=max(32, cycles * 3 + 8),
        )
        acknowledgements = duplicates = redeliveries = restart_failures = 0
        legal_content_present = False
        for cycle in range(1, cycles + 1):
            envelope = {
                "type": "BLOCK_ANNOUNCE",
                "from_node_id": f"office-{index + 1}",
                "from_val_id": f"validator-{index + 1}",
                "chain_id": chain_id,
                "ts_ms": int(self.clock_ms()) + cycle,
                "payload": {"height": cycle, "block_id": f"network-{index + 1}-block-{cycle}"},
                "hops": 0,
            }
            target = f"intermittent-{index + 1}"
            first = relay.put(
                from_node_id=envelope["from_node_id"], target_node_id=target,
                envelope=envelope, ttl_ms=60_000,
            )
            duplicate = relay.put(
                from_node_id=envelope["from_node_id"], target_node_id=target,
                envelope=envelope, ttl_ms=60_000,
            )
            duplicates += int(bool(duplicate.get("duplicate")))
            if cycle % restart_interval == 0:
                relay = NATRelayStore(
                    network_root / "relay", chain_id=chain_id, limits=limits, clock_ms=self.clock_ms,
                )
                recovery = PartitionRecoveryStore(
                    network_root / "partition", chain_id=chain_id,
                    node_id=f"intermittent-{index + 1}", clock_ms=self.clock_ms,
                    max_events=max(32, cycles * 3 + 8),
                )
                if relay.count_for(target) != 1:
                    restart_failures += 1
            first_pull = relay.pull(target_node_id=target)
            second_pull = relay.pull(target_node_id=target)
            redeliveries += int(
                len(first_pull["messages"]) == 1
                and len(second_pull["messages"]) == 1
                and int(second_pull["messages"][0]["delivery_attempts"]) == 2
            )
            acknowledgements += int(
                relay.ack(target_node_id=target, relay_ids=[str(first["relay_id"])])["acknowledged"] == 1
            )
            encoded = _canonical(envelope).lower()
            legal_content_present = legal_content_present or any(
                value in encoded for value in (b"document_body", b"signer_email", b"legal_matter", b"attachment")
            )
            if cycle == max(2, cycles // 2):
                halted = recovery.transition(
                    PHASE_SAFETY_HALT, reason="soak_conflicting_trusted_finality_views",
                    conflict_digest="sha256:" + sha256(f"{chain_id}:{cycle}".encode()).hexdigest(),
                    conflicting_heights=[cycle], local_finalized_height=cycle - 1,
                )
                recovery.clear_safety_halt(
                    halt_id=str(halted["halt_id"]), operator_id="soak-operator",
                    reason="bounded exercise checkpoint review",
                    confirmation="CLEAR GLYPHCHAIN PARTITION SAFETY HALT",
                )
            recovery.transition(
                PHASE_BLOCK_CATCHUP, reason="soak_interruption_recovery",
                local_finalized_height=max(0, cycle - 1), target_finalized_height=cycle,
                missing_from_height=cycle, missing_to_height=cycle,
            )
            recovery.transition(
                PHASE_HEALTHY, reason="soak_block_materialized", local_finalized_height=cycle,
            )
        return {
            "network_commitment": sha256(chain_id.encode("utf-8")).hexdigest(),
            "messages_acknowledged": acknowledgements,
            "duplicate_puts_idempotent": duplicates,
            "redeliveries_observed": redeliveries,
            "restart_failures": restart_failures,
            "partition_journal_valid": recovery.verify_journal(),
            "partition_event_count": int(recovery.status()["event_sequence"]),
            "final_partition_phase": recovery.status()["phase"],
            "relay_queue_final_depth": relay.status()["queued_messages"],
            "legal_content_present": legal_content_present,
        }

    def _cross_network_isolation(self, network_count: int) -> bool:
        first_chain = "glyphchain-soak-1"
        foreign_chain = f"glyphchain-soak-{network_count}"
        store = NATRelayStore(
            self.root / "network-1" / "relay", chain_id=first_chain,
            clock_ms=self.clock_ms,
        )
        try:
            store.put(
                from_node_id="foreign-node", target_node_id="local-node", ttl_ms=30_000,
                envelope={
                    "type": "BLOCK_ANNOUNCE", "from_node_id": "foreign-node",
                    "from_val_id": "foreign-validator", "chain_id": foreign_chain,
                    "ts_ms": int(self.clock_ms()), "payload": {"height": 1}, "hops": 0,
                },
            )
        except NATRelayError as exc:
            return str(exc) == "nat_relay_envelope_chain_mismatch"
        return False

    def _prepare_root(self) -> None:
        requested = self.root.expanduser()
        if requested.is_symlink():
            raise NetworkSoakQualificationError("network soak root symlink refused")
        resolved = Path(os.path.realpath(requested))
        if resolved.exists() and any(resolved.iterdir()):
            raise NetworkSoakQualificationError("network soak root must be empty")
        resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root = resolved

    @staticmethod
    def verify_report(report: Mapping[str, Any]) -> bool:
        value = dict(report)
        supplied = str(value.pop("report_sha256", ""))
        return bool(supplied) and hmac.compare_digest(supplied, sha256(_canonical(value)).hexdigest())

    @staticmethod
    def write_report(path: str | Path, report: Mapping[str, Any]) -> Path:
        requested = Path(path).expanduser()
        if requested.is_symlink():
            raise NetworkSoakQualificationError("network soak report symlink refused")
        output = Path(os.path.realpath(requested))
        if output.suffix.lower() != ".json":
            raise NetworkSoakQualificationError("network soak report must be JSON")
        output.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(dict(report), indent=2, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            output.unlink(missing_ok=True)
            raise
        return output
