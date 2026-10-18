"""Content-free pre-production qualification for GlyphChain network controls.

The exercise uses independent durable stores for four logical device profiles.
It is deliberately not a substitute for separate physical devices, real NAT,
an independently operated relay, or a production security approval.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
from typing import Any, Iterator, Mapping

from backend.modules.consensus.partition_recovery import (
    PHASE_BLOCK_CATCHUP,
    PHASE_HEALTHY,
    PHASE_REJOIN_ASSESSING,
    PHASE_SAFETY_HALT,
    PartitionRecoveryStore,
    classify_validated_views,
)
from backend.modules.consensus.protocol_upgrade import (
    EXACT_COMPLETE_CONFIRMATION,
    EXACT_SCHEDULE_CONFIRMATION,
    ProtocolUpgradeStore,
)
from backend.modules.p2p.nat_relay import NATRelayLimits, NATRelayStore


class NetworkQualificationError(ValueError):
    pass


SCHEMA_VERSION = "glyphchain.network-qualification.v1"
LOGICAL_PROFILES = ("home", "office", "vm", "intermittent")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hex_digest(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized[7:]
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise NetworkQualificationError("network qualification requires an exact SHA-256 release manifest digest")
    return normalized


@contextmanager
def _protocol_support(version: int) -> Iterator[None]:
    names = ("GLYPHCHAIN_PROTOCOL_MIN_SUPPORTED", "GLYPHCHAIN_PROTOCOL_MAX_SUPPORTED")
    previous = {name: os.environ.get(name) for name in names}
    os.environ[names[0]] = "1"
    os.environ[names[1]] = str(version)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class NetworkQualificationExercise:
    """Run bounded local simulations and emit a content-free evidence report."""

    def __init__(self, root: str | Path, *, clock_ms: Any | None = None) -> None:
        self.root = Path(root)
        self.clock_ms = clock_ms or (lambda: int(datetime.now(timezone.utc).timestamp() * 1000))

    def run(
        self,
        *,
        release_manifest_sha256: str,
        validator_checkpoint_id: str,
        governance_approval_id: str,
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        release_digest = _hex_digest(release_manifest_sha256)
        checkpoint = str(validator_checkpoint_id or "").strip()
        approval = str(governance_approval_id or "").strip()
        if not checkpoint or not approval:
            raise NetworkQualificationError("checkpoint and governance approval identifiers are required")
        self._prepare_root()

        relay = self._exercise_relay()
        partition = self._exercise_partition_recovery()
        upgrade = self._exercise_protocol_upgrade(
            release_digest=release_digest,
            checkpoint_id=checkpoint,
            approval_id=approval,
        )
        checks = {
            "four_logical_device_profiles": len(upgrade["node_commitments"]) == len(LOGICAL_PROFILES),
            "relay_restart_preserved_message": relay["restart_preserved_message"],
            "delayed_message_redelivery_then_ack": relay["delayed_redelivery_then_ack"],
            "duplicate_relay_put_idempotent": relay["duplicate_put_idempotent"],
            "relay_payload_excludes_legal_content": relay["legal_content_present"] is False,
            "partition_conflict_failed_closed": partition["conflict_entered_safety_halt"],
            "partition_clearance_required_exact_halt": partition["exact_halt_cleared_to_rejoin"],
            "partition_catchup_returned_healthy": partition["catchup_returned_healthy"],
            "upgrade_bound_exact_release_manifest": upgrade["release_manifest_sha256"] == release_digest,
            "upgrade_quorum_ready_at_activation": upgrade["quorum_ready_at_activation"],
            "upgrade_survived_all_node_restarts": upgrade["all_nodes_restarted_on_target_version"],
        }
        passed = all(checks.values())
        report: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at or _now(),
            "result": "LOCAL_PREPRODUCTION_EXERCISE_PASSED" if passed else "FAILED",
            "content_free": True,
            "claim_boundary": (
                "Four logical profiles were exercised on one local machine. This is not evidence of "
                "separate physical devices, real carrier or enterprise NAT, an independently operated "
                "public relay, production availability, or operational approval."
            ),
            "logical_profiles": list(LOGICAL_PROFILES),
            "checks": checks,
            "relay": relay,
            "partition_recovery": partition,
            "protocol_upgrade": upgrade,
            "production_ready": False,
            "remaining_external_gates": [
                "approved malicious-validator and emergency-removal procedure",
                "representative independent home, office, VM and intermittent devices",
                "real NAT, delay, reconnect, relay outage and partition exercise",
                "multi-device signed-release activation exercise",
                "production-like independently operated public relay validation",
            ],
        }
        report["report_sha256"] = sha256(_canonical(report)).hexdigest()
        if not passed:
            raise NetworkQualificationError("local network qualification exercise failed")
        return report

    def _prepare_root(self) -> None:
        requested = self.root.expanduser()
        if requested.is_symlink():
            raise NetworkQualificationError("network qualification root symlink refused")
        absolute = Path(os.path.realpath(requested))
        for component in (absolute, *absolute.parents):
            if component.is_symlink():
                raise NetworkQualificationError("network qualification root symlink refused")
        if absolute.exists() and any(absolute.iterdir()):
            raise NetworkQualificationError("network qualification root must be empty")
        absolute.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(absolute, 0o700)
        except OSError:
            pass
        self.root = absolute

    def _exercise_relay(self) -> dict[str, Any]:
        relay_root = self.root / "relay"
        limits = NATRelayLimits(
            maximum_messages=16, maximum_per_target=8,
            maximum_message_bytes=4096, maximum_ttl_ms=120_000, pull_batch=8,
        )
        store = NATRelayStore(relay_root, chain_id="glyphchain-qualification", limits=limits, clock_ms=self.clock_ms)
        envelope = {
            "type": "BLOCK_ANNOUNCE",
            "from_node_id": "office-node",
            "from_val_id": "validator-office",
            "chain_id": "glyphchain-qualification",
            "ts_ms": int(self.clock_ms()),
            "payload": {"height": 41, "block_id": "qualification-block-41"},
            "hops": 0,
        }
        first = store.put(
            from_node_id="office-node", target_node_id="intermittent-node",
            envelope=envelope, ttl_ms=60_000,
        )
        duplicate = store.put(
            from_node_id="office-node", target_node_id="intermittent-node",
            envelope=envelope, ttl_ms=60_000,
        )
        restarted = NATRelayStore(
            relay_root, chain_id="glyphchain-qualification", limits=limits, clock_ms=self.clock_ms,
        )
        first_pull = restarted.pull(target_node_id="intermittent-node")
        second_pull = restarted.pull(target_node_id="intermittent-node")
        relay_id = str(first["relay_id"])
        acknowledged = restarted.ack(target_node_id="intermittent-node", relay_ids=[relay_id])
        serialized = _canonical(envelope).lower()
        forbidden = (b"document_body", b"signer_email", b"legal_matter", b"attachment")
        return {
            "restart_preserved_message": [item["relay_id"] for item in first_pull["messages"]] == [relay_id],
            "delayed_redelivery_then_ack": (
                second_pull["messages"][0]["delivery_attempts"] == 2
                and acknowledged["acknowledged"] == 1
                and restarted.status()["queued_messages"] == 0
            ),
            "duplicate_put_idempotent": bool(duplicate.get("duplicate")) and duplicate.get("relay_id") == relay_id,
            "legal_content_present": any(value in serialized for value in forbidden),
            "relay_id_commitment": sha256(relay_id.encode("utf-8")).hexdigest(),
        }

    def _exercise_partition_recovery(self) -> dict[str, Any]:
        store = PartitionRecoveryStore(
            self.root / "partition", chain_id="glyphchain-qualification",
            node_id="intermittent-node", clock_ms=self.clock_ms,
        )
        classification = classify_validated_views(
            [
                {"height": 42, "round": 0, "block_id": "block-42-a"},
                {"height": 42, "round": 1, "block_id": "block-42-b"},
            ],
            local_height=41,
            local_block_id="qualification-block-41",
        )
        halted = store.transition(
            PHASE_SAFETY_HALT,
            reason=classification["reason"],
            conflict_digest=classification["conflict_digest"],
            conflicting_heights=classification["conflicting_heights"],
            local_finalized_height=41,
        )
        restarted = PartitionRecoveryStore(
            self.root / "partition", chain_id="glyphchain-qualification",
            node_id="intermittent-node", clock_ms=self.clock_ms,
        )
        cleared = restarted.clear_safety_halt(
            halt_id=str(halted["halt_id"]), operator_id="qualification-operator",
            reason="independent checkpoint reviewed in bounded exercise",
            confirmation="CLEAR GLYPHCHAIN PARTITION SAFETY HALT",
        )
        catchup = restarted.transition(
            PHASE_BLOCK_CATCHUP, reason="trusted_higher_finality_available",
            local_finalized_height=41, target_finalized_height=43,
            missing_from_height=42, missing_to_height=43,
        )
        healthy = restarted.transition(
            PHASE_HEALTHY, reason="verified_blocks_materialized",
            local_finalized_height=43,
        )
        return {
            "conflict_entered_safety_halt": classification["phase"] == PHASE_SAFETY_HALT and restarted.verify_journal(),
            "exact_halt_cleared_to_rejoin": cleared["phase"] == PHASE_REJOIN_ASSESSING,
            "catchup_returned_healthy": catchup["phase"] == PHASE_BLOCK_CATCHUP and healthy["phase"] == PHASE_HEALTHY,
            "halt_id_commitment": sha256(str(halted["halt_id"]).encode("utf-8")).hexdigest(),
            "journal_event_count": int(healthy["event_sequence"]),
        }

    def _exercise_protocol_upgrade(self, *, release_digest: str, checkpoint_id: str, approval_id: str) -> dict[str, Any]:
        activation_height = 120
        powers = {f"validator-{profile}": 1 for profile in LOGICAL_PROFILES}
        stores: dict[str, ProtocolUpgradeStore] = {}
        plans: dict[str, dict[str, Any]] = {}
        with _protocol_support(2):
            for profile in LOGICAL_PROFILES:
                store = ProtocolUpgradeStore(
                    self.root / "upgrade" / profile,
                    chain_id="glyphchain-qualification", node_id=f"{profile}-node",
                    clock_ms=self.clock_ms,
                )
                plan = store.schedule(
                    target_version=2, activation_height=activation_height,
                    release_manifest_sha256=release_digest,
                    validator_checkpoint_id=checkpoint_id,
                    governance_approval_id=approval_id,
                    operator_id="qualification-operator",
                    confirmation=EXACT_SCHEDULE_CONFIRMATION,
                    current_finalized_height=10,
                )["plan"]
                stores[profile] = store
                plans[profile] = plan
            plan_ids = {str(plan["plan_id"]) for plan in plans.values()}
            advertisements = {
                profile: stores[profile].advertisement(finalized_height=119)
                for profile in LOGICAL_PROFILES
            }
            assessments: dict[str, Mapping[str, Any]] = {}
            for profile in LOGICAL_PROFILES:
                peers = [
                    {"validator_id": f"validator-{other}", "protocol": advertisements[other]}
                    for other in LOGICAL_PROFILES if other != profile
                ]
                assessments[profile] = stores[profile].assess(
                    next_height=activation_height,
                    validator_powers=powers,
                    self_validator_id=f"validator-{profile}",
                    peer_advertisements=peers,
                )
            for store in stores.values():
                store.complete(
                    operator_id="qualification-operator",
                    confirmation=EXACT_COMPLETE_CONFIRMATION,
                    current_finalized_height=activation_height,
                )
            restarted_versions = {
                profile: ProtocolUpgradeStore(
                    self.root / "upgrade" / profile,
                    chain_id="glyphchain-qualification", node_id=f"{profile}-node",
                    clock_ms=self.clock_ms,
                ).status()["current_protocol_version"]
                for profile in LOGICAL_PROFILES
            }
        return {
            "release_manifest_sha256": release_digest,
            "validator_checkpoint_id_commitment": sha256(checkpoint_id.encode("utf-8")).hexdigest(),
            "governance_approval_id_commitment": sha256(approval_id.encode("utf-8")).hexdigest(),
            "activation_height": activation_height,
            "single_plan_id_across_nodes": len(plan_ids) == 1,
            "quorum_ready_at_activation": len(plan_ids) == 1 and all(
                item["phase"] == "ACTIVE" and item["consensus_allowed"]
                for item in assessments.values()
            ),
            "all_nodes_restarted_on_target_version": all(value == 2 for value in restarted_versions.values()),
            "node_commitments": {
                profile: sha256(f"{profile}-node".encode("utf-8")).hexdigest()
                for profile in LOGICAL_PROFILES
            },
        }

    @staticmethod
    def verify_report(report: Mapping[str, Any]) -> bool:
        value = dict(report)
        supplied = str(value.pop("report_sha256", ""))
        return bool(supplied) and hmac.compare_digest(supplied, sha256(_canonical(value)).hexdigest())

    @staticmethod
    def write_report(path: str | Path, report: Mapping[str, Any]) -> Path:
        requested = Path(path).expanduser()
        if requested.is_symlink():
            raise NetworkQualificationError("network qualification report symlink refused")
        output = Path(os.path.realpath(requested))
        if output.suffix.lower() != ".json":
            raise NetworkQualificationError("network qualification report must be JSON")
        for component in (output, *output.parents):
            if component.is_symlink():
                raise NetworkQualificationError("network qualification report symlink refused")
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
