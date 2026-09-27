from __future__ import annotations

import json
from types import SimpleNamespace

from backend.modules.p2p.network_health import NetworkHealthStore, build_health_snapshot


def _consensus(**overrides):
    value = {
        "chain_id": "private-business-chain",
        "network_participation": {"role": "light"},
        "finalized_height": 12,
        "height": 13,
        "round": 0,
        "last_qc": {"height": 12, "block_id": "block-12", "ts_ms": 9_999_000},
        "recent_qcs": [{"height": 12, "block_id": "block-12"}],
        "quorum_finality": {"enabled": True, "latest_certificate": {"schema_version": "v2"}},
        "finality_latency_ms_last": 20,
        "finality_latency_ms_p50": 18,
        "finality_latency_ms_p95": 25,
        "finality_latency_ms_samples": 4,
    }
    value.update(overrides)
    return value


def test_snapshot_contains_only_aggregate_peer_and_network_data():
    snapshot = build_health_snapshot(
        consensus=_consensus(),
        peers=[SimpleNamespace(node_id="secret-node", base_url="https://private.example", role="validator", hello_ok=True,
                               banned=False, last_seen_ms=9_999_500)],
        peer_limit=100,
        ingress={"lanes": {}},
        now_ms=10_000_000,
    )
    encoded = json.dumps(snapshot)
    assert snapshot["status"] == "healthy"
    assert snapshot["peers"]["verified_validators"] == 1
    assert snapshot["network_digest"].startswith("sha256:")
    assert "secret-node" not in encoded
    assert "private.example" not in encoded
    assert "private-business-chain" not in encoded


def test_snapshot_detects_conflicting_finality_stall_and_ingress_drop(monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_FINALITY_STALE_AFTER_MS", "1000")
    snapshot = build_health_snapshot(
        consensus=_consensus(
            network_participation={"role": "validator"},
            height=20,
            round=5,
            recent_qcs=[{"height": 12, "block_id": "a"}, {"height": 12, "block_id": "b"}],
            quorum_finality={"enabled": True, "latest_certificate": None},
        ),
        peers=[],
        peer_limit=8,
        ingress={"lanes": {"vote": {"queue_len": 2, "queue_max": 2, "counters": {"dropped_full": 4}}}},
        ledger_storage={"near_capacity": True, "at_capacity": False, "used_bytes": 950, "max_bytes": 1000},
        previous={"ingress": {"dropped_full": 1}},
        now_ms=10_010_000,
    )
    codes = {item["code"] for item in snapshot["alerts"]}
    assert snapshot["status"] == "critical"
    assert {"conflicting_finality_history", "finality_height_lag", "extended_consensus_round",
            "finality_stale", "no_verified_peers", "ingress_capacity_drop",
            "portable_finality_certificate_missing"}.issubset(codes)
    assert "ledger_storage_near_capacity" in codes


def test_snapshot_surfaces_partition_recovery_without_exposing_halt_identity():
    snapshot = build_health_snapshot(
        consensus=_consensus(partition_recovery={
            "phase": "SAFETY_HALT",
            "halt_id": "secret-halt-id",
            "local_finalized_height": 12,
            "target_finalized_height": 12,
            "recovery_attempts": 2,
            "state_readable": True,
            "journal_valid": True,
        }),
        peers=[], peer_limit=8, ingress={"lanes": {}}, now_ms=10_000_000,
    )
    codes = {item["code"] for item in snapshot["alerts"]}
    assert "partition_recovery_safety_halt" in codes
    assert snapshot["status"] == "critical"
    assert snapshot["partition_recovery"]["phase"] == "SAFETY_HALT"
    assert "secret-halt-id" not in json.dumps(snapshot)


def test_snapshot_surfaces_protocol_activation_halt_without_release_secrets():
    snapshot = build_health_snapshot(
        consensus=_consensus(protocol_upgrade={
            "phase": "UPGRADE_HALT", "active_version": 1,
            "ready_power": 1, "quorum_power": 2,
            "mismatched_validator_count": 1,
            "release_manifest_sha256": "secret-release-digest",
        }),
        peers=[], peer_limit=8, ingress={"lanes": {}}, now_ms=10_000_000,
    )
    assert snapshot["status"] == "critical"
    assert "protocol_upgrade_halt" in {item["code"] for item in snapshot["alerts"]}
    assert snapshot["protocol_upgrade"]["ready_power"] == 1
    assert "secret-release-digest" not in json.dumps(snapshot)


def test_bounded_health_history_is_hash_chained_and_detects_tampering(tmp_path):
    store = NetworkHealthStore(tmp_path, max_records=8)
    for height in range(12):
        store.append(build_health_snapshot(
            consensus=_consensus(finalized_height=height, height=height + 1),
            peers=[], peer_limit=8, ingress={"lanes": {}}, now_ms=10_000_000 + height,
        ))
    assert len(store.history(limit=100)) == 8
    assert store.verify() is True
    lines = store.path.read_text(encoding="utf-8").splitlines()
    altered = json.loads(lines[3])
    altered["status"] = "critical"
    lines[3] = json.dumps(altered, sort_keys=True, separators=(",", ":"))
    store.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert store.verify() is False
