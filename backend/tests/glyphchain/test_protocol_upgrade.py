from __future__ import annotations

import pytest

from backend.modules.consensus.protocol_upgrade import (
    EXACT_CANCEL_CONFIRMATION,
    EXACT_COMPLETE_CONFIRMATION,
    EXACT_SCHEDULE_CONFIRMATION,
    ProtocolUpgradeError,
    ProtocolUpgradeStore,
)
from backend.modules.p2p.crypto_ed25519 import (
    canonical_hello_sign_bytes,
    pubkey_from_priv,
    sign_ed25519,
    verify_ed25519,
)


RELEASE = "ab" * 32


def _schedule(store: ProtocolUpgradeStore):
    return store.schedule(
        target_version=2,
        activation_height=150,
        release_manifest_sha256=RELEASE,
        validator_checkpoint_id="checkpoint-1",
        governance_approval_id="approval-1",
        operator_id="operator-1",
        confirmation=EXACT_SCHEDULE_CONFIRMATION,
        current_finalized_height=10,
    )


def test_protocol_upgrade_plan_is_durable_hash_chained_and_cancelled_only_before_activation(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_PROTOCOL_UPGRADE_MIN_LEAD_BLOCKS", "100")
    store = ProtocolUpgradeStore(tmp_path, chain_id="chain-1", node_id="node-1", clock_ms=lambda: 1000)
    state = _schedule(store)
    assert state["plan"]["plan_id"].startswith("sha256:")
    assert store.verify_journal() is True
    assert ProtocolUpgradeStore(tmp_path, chain_id="chain-1", node_id="node-1").status()["plan"]["target_version"] == 2
    with pytest.raises(ProtocolUpgradeError):
        store.cancel(operator_id="operator-1", reason="bad release", confirmation=EXACT_CANCEL_CONFIRMATION, current_finalized_height=150)
    cancelled = store.cancel(operator_id="operator-1", reason="bad release", confirmation=EXACT_CANCEL_CONFIRMATION, current_finalized_height=149)
    assert cancelled["plan"] is None
    assert store.verify_journal() is True


def test_activation_halts_without_supported_quorum_and_allows_matching_quorum(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_PROTOCOL_UPGRADE_MIN_LEAD_BLOCKS", "1")
    monkeypatch.setenv("GLYPHCHAIN_PROTOCOL_MAX_SUPPORTED", "2")
    store = ProtocolUpgradeStore(tmp_path, chain_id="chain-1", node_id="node-1")
    plan = store.schedule(
        target_version=2, activation_height=20, release_manifest_sha256=RELEASE,
        validator_checkpoint_id="checkpoint-1", governance_approval_id="approval-1",
        operator_id="operator-1", confirmation=EXACT_SCHEDULE_CONFIRMATION,
        current_finalized_height=10,
    )["plan"]
    powers = {"val-1": 1, "val-2": 1, "val-3": 1}
    halted = store.assess(next_height=20, validator_powers=powers, self_validator_id="val-1", peer_advertisements=[])
    assert halted["phase"] == "UPGRADE_HALT"
    assert halted["consensus_allowed"] is False
    ready = store.assess(next_height=20, validator_powers=powers, self_validator_id="val-1", peer_advertisements=[
        {"validator_id": "val-2", "protocol": {"plan_id": plan["plan_id"], "supported_max": 2}},
    ])
    assert ready["phase"] == "ACTIVE"
    assert ready["ready_power"] == ready["quorum_power"] == 2


def test_unsupported_local_release_fails_closed_and_completion_commits_version(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_PROTOCOL_UPGRADE_MIN_LEAD_BLOCKS", "1")
    monkeypatch.setenv("GLYPHCHAIN_PROTOCOL_MAX_SUPPORTED", "1")
    store = ProtocolUpgradeStore(tmp_path, chain_id="chain-1", node_id="node-1")
    plan = store.schedule(
        target_version=2, activation_height=20, release_manifest_sha256=RELEASE,
        validator_checkpoint_id="checkpoint-1", governance_approval_id="approval-1",
        operator_id="operator-1", confirmation=EXACT_SCHEDULE_CONFIRMATION,
        current_finalized_height=10,
    )["plan"]
    assessment = store.assess(next_height=20, validator_powers={"val-1": 2}, self_validator_id="val-1", peer_advertisements=[])
    assert assessment["consensus_allowed"] is False
    assert assessment["local_target_supported"] is False
    with pytest.raises(ProtocolUpgradeError):
        store.complete(operator_id="operator-1", confirmation=EXACT_COMPLETE_CONFIRMATION, current_finalized_height=20)
    monkeypatch.setenv("GLYPHCHAIN_PROTOCOL_MAX_SUPPORTED", "2")
    completed = store.complete(operator_id="operator-1", confirmation=EXACT_COMPLETE_CONFIRMATION, current_finalized_height=20)
    assert completed["current_protocol_version"] == plan["target_version"]
    assert completed["plan"] is None


def test_protocol_advertisement_is_bound_into_signed_hello():
    private = "11" * 32
    public = pubkey_from_priv(private)
    protocol = {
        "schema_version": "glyphchain.protocol-upgrade.v1",
        "active_version": 1,
        "supported_min": 1,
        "supported_max": 2,
        "plan_id": "sha256:" + "22" * 32,
        "target_version": 2,
        "activation_height": 100,
    }
    signed = canonical_hello_sign_bytes(
        chain_id="chain-1", node_id="node-1", val_id="val-1",
        base_url="https://node.example", pubkey_hex=public, protocol=protocol,
    )
    signature = sign_ed25519(private, signed)
    assert verify_ed25519(public, signature, signed)
    changed = dict(protocol); changed["supported_max"] = 99
    tampered = canonical_hello_sign_bytes(
        chain_id="chain-1", node_id="node-1", val_id="val-1",
        base_url="https://node.example", pubkey_hex=public, protocol=changed,
    )
    assert verify_ed25519(public, signature, tampered) is False
