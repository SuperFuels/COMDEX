from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.consensus.finality_certificate import build_finality_certificate, vote_sign_bytes
from backend.modules.consensus.finality_checkpoint import CHECKPOINT_SCHEMA, normalize_checkpoint
from backend.modules.consensus.ledger_commitment import empty_ledger_block, normalize_ledger_block
from backend.modules.consensus.partition_recovery import (
    PHASE_BLOCK_CATCHUP,
    PHASE_REJOIN_ASSESSING,
    PHASE_SAFETY_HALT,
    PartitionRecoveryError,
    PartitionRecoveryStore,
    classify_validated_views,
)
from backend.modules.consensus.types import QC


def test_partition_recovery_store_is_durable_hash_chained_and_halt_is_sticky(tmp_path):
    now = [1_700_000_000_000]
    store = PartitionRecoveryStore(
        tmp_path / "recovery",
        chain_id="glyphchain-test",
        node_id="node-1",
        clock_ms=lambda: now[0],
    )
    catchup = store.transition(
        PHASE_BLOCK_CATCHUP,
        reason="trusted_higher_finality_available",
        local_finalized_height=5,
        target_finalized_height=9,
        missing_from_height=6,
        missing_to_height=9,
    )
    assert catchup["target_finalized_height"] == 9
    now[0] += 1
    halted = store.transition(
        PHASE_SAFETY_HALT,
        reason="conflicting_trusted_finality_views",
        conflict_digest="sha256:" + "a" * 64,
        conflicting_heights=[9],
    )
    assert halted["halt_id"].startswith("sha256:")
    assert store.verify_journal() is True

    restarted = PartitionRecoveryStore(
        tmp_path / "recovery",
        chain_id="glyphchain-test",
        node_id="node-1",
        clock_ms=lambda: now[0],
    )
    assert restarted.status()["phase"] == PHASE_SAFETY_HALT
    with pytest.raises(PartitionRecoveryError, match="explicit administrator clearance"):
        restarted.transition(PHASE_BLOCK_CATCHUP, reason="peer_looks_healthy")
    with pytest.raises(PartitionRecoveryError, match="confirmation required"):
        restarted.clear_safety_halt(
            halt_id=halted["halt_id"], operator_id="owner-1", reason="reviewed evidence", confirmation="CLEAR",
        )
    cleared = restarted.clear_safety_halt(
        halt_id=halted["halt_id"],
        operator_id="owner-1",
        reason="independent checkpoint review completed",
        confirmation="CLEAR GLYPHCHAIN PARTITION SAFETY HALT",
    )
    assert cleared["phase"] == PHASE_REJOIN_ASSESSING
    assert restarted.verify_journal() is True


def test_partition_view_classification_detects_peer_and_local_finality_conflicts():
    views = [
        {"height": 12, "round": 0, "block_id": "h12-r0-Pval-3"},
        {"height": 12, "round": 1, "block_id": "h12-r1-Pval-1"},
    ]
    peer_conflict = classify_validated_views(views, local_height=10, local_block_id="h10-r0-Pval-1")
    assert peer_conflict["phase"] == PHASE_SAFETY_HALT
    assert peer_conflict["conflicting_heights"] == [12]

    local_conflict = classify_validated_views(
        [{"height": 10, "round": 1, "block_id": "h10-r1-Pval-2"}],
        local_height=10,
        local_block_id="h10-r0-Pval-1",
    )
    assert local_conflict["phase"] == PHASE_SAFETY_HALT

    healthy_ahead = classify_validated_views(
        [{"height": 13, "round": 0, "block_id": "h13-r0-Pval-1", "payload_index": 0}],
        local_height=10,
        local_block_id="h10-r0-Pval-1",
    )
    assert healthy_ahead["phase"] == PHASE_BLOCK_CATCHUP
    assert healthy_ahead["candidate"]["height"] == 13


def _configure_engine(monkeypatch, tmp_path):
    monkeypatch.setenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-partition-test")
    monkeypatch.setenv("GLYPHCHAIN_NETWORK_ID", "testnet")
    monkeypatch.setenv("GLYPHCHAIN_NODE_ID", "node-1")
    monkeypatch.setenv("GLYPHCHAIN_VALIDATORS", "val-1:1,val-2:1,val-3:1")
    monkeypatch.setenv("GLYPHCHAIN_SELF_VAL_ID", "val-1")
    monkeypatch.setenv("GLYPHCHAIN_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(tmp_path / "ledger.sqlite3"))
    monkeypatch.setenv("CONSENSUS_SYNC_ENABLE", "1")
    monkeypatch.delenv("GLYPHCHAIN_FINALITY_CHECKPOINT_JSON", raising=False)
    monkeypatch.delenv("GLYPHCHAIN_TRUSTED_CHECKPOINT_ID", raising=False)
    from backend.modules.chain_sim.chain_sim_ledger import reset_ledger
    reset_ledger(clear_persist=True)


def _tip_payload(engine, height: int) -> dict:
    block = empty_ledger_block(height=height)
    commitment = normalize_ledger_block(block, chain_id=engine.chain_id, height=height)
    leader = engine.leader_for(height, 0)
    block_id = f"h{height}-r0-P{leader}-C{commitment['ledger_commitment']}"
    qc = QC(
        height=height,
        round=0,
        vote_type="PRECOMMIT",
        block_id=block_id,
        voters=["val-1", "val-2"],
        ledger_commitment=commitment["ledger_commitment"],
        txs_root=commitment["txs_root"],
    )
    return {"finalized_height": height, "round": 0, "last_qc": qc.model_dump()}


@pytest.mark.asyncio
async def test_partition_sync_never_advances_tip_before_exact_blocks_are_materialized(monkeypatch, tmp_path):
    _configure_engine(monkeypatch, tmp_path)
    from backend.modules.consensus import engine as engine_module

    engine = engine_module.ConsensusEngine()
    payload = _tip_payload(engine, 2)
    monkeypatch.setattr(engine, "_peers_snapshot", lambda: [{
        "base_url": "https://peer.invalid",
        "node_id": "node-2",
        "val_id": "val-2",
        "hello_ok": True,
    }])

    async def sync_one(**_kwargs):
        return {"ok": True, "payload": payload}

    async def unavailable_block(**_kwargs):
        return {"ok": False, "error": "partition still active"}

    monkeypatch.setattr(engine_module, "request_sync_one", sync_one)
    monkeypatch.setattr(engine_module, "request_block", unavailable_block)
    await engine._sync_once()
    assert engine.status()["finalized_height"] == 0
    recovery = engine.status()["partition_recovery"]
    assert recovery["phase"] == PHASE_BLOCK_CATCHUP
    assert recovery["target_finalized_height"] == 2

    async def available_block(*, height, **_kwargs):
        return {"ok": True, "block": empty_ledger_block(height=height)}

    # Clear per-peer backoff from the intentionally failed attempt so the next
    # deterministic recovery cycle can exercise successful materialization.
    engine._sync_policy.min_spacing_ms = 0
    engine._sync_policy.base_ms = 0
    engine._sync_policy.max_ms = 0
    monkeypatch.setattr(engine_module, "request_block", available_block)
    await engine._sync_once()
    status = engine.status()
    assert status["finalized_height"] == 2
    assert status["last_qc"]["block_id"] == payload["last_qc"]["block_id"]
    assert status["partition_recovery"]["phase"] == "HEALTHY"


@pytest.mark.asyncio
async def test_partition_conflict_enters_sticky_halt_and_suppresses_consensus_actions(monkeypatch, tmp_path):
    _configure_engine(monkeypatch, tmp_path)
    from backend.modules.consensus import engine as engine_module

    engine = engine_module.ConsensusEngine()
    first = _tip_payload(engine, 1)
    monkeypatch.setattr(engine, "_peers_snapshot", lambda: [{
        "base_url": "https://peer.invalid", "node_id": "node-2", "val_id": "val-2", "hello_ok": True,
    }])

    async def sync_first(**_kwargs):
        return {"ok": True, "payload": first}

    async def block_one(*, height, **_kwargs):
        return {"ok": True, "block": empty_ledger_block(height=height)}

    monkeypatch.setattr(engine_module, "request_sync_one", sync_first)
    monkeypatch.setattr(engine_module, "request_block", block_one)
    engine._sync_policy.min_spacing_ms = 0
    await engine._sync_once()
    assert engine.status()["finalized_height"] == 1

    commitment = normalize_ledger_block(empty_ledger_block(height=1), chain_id=engine.chain_id, height=1)
    conflicting = QC(
        height=1,
        round=1,
        vote_type="PRECOMMIT",
        block_id=f"h1-r1-P{engine.leader_for(1, 1)}-C{commitment['ledger_commitment']}",
        voters=["val-1", "val-2"],
        ledger_commitment=commitment["ledger_commitment"],
        txs_root=commitment["txs_root"],
    )
    result = engine.handle_sync_resp({"finalized_height": 1, "last_qc": conflicting.model_dump()})
    assert result["ok"] is False
    assert engine.status()["partition_recovery"]["phase"] == PHASE_SAFETY_HALT
    halted_vote = engine.handle_vote(type("VoteLike", (), {
        "height": 2, "round": 0, "voter": "val-1", "vote_type": "PREVOTE", "block_id": "irrelevant",
    })())
    assert halted_vote["accepted"] is False
    assert halted_vote["reason"] == "partition recovery safety halt"


def test_verified_snapshot_advances_large_gap_consensus_only_after_tip_binding(monkeypatch, tmp_path):
    keys = [Ed25519PrivateKey.generate() for _ in range(3)]
    validators = [{
        "validator_id": f"val-{index + 1}",
        "power": 1,
        "public_key_base64": base64.b64encode(key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )).decode("ascii"),
    } for index, key in enumerate(keys)]
    checkpoint_raw = {
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": "glyphchain-partition-test",
        "network_id": "testnet",
        "epoch": 0,
        "effective_height": 1,
        "validator_set": validators,
    }
    checkpoint = normalize_checkpoint(checkpoint_raw)
    _configure_engine(monkeypatch, tmp_path)
    monkeypatch.setenv("GLYPHCHAIN_FINALITY_CHECKPOINT_JSON", json.dumps(checkpoint_raw))
    monkeypatch.setenv("GLYPHCHAIN_TRUSTED_CHECKPOINT_ID", checkpoint["checkpoint_id"])
    monkeypatch.setenv("GLYPHCHAIN_FINALITY_PRIVKEY_HEX", keys[0].private_bytes_raw().hex())
    from backend.modules.consensus.engine import ConsensusEngine

    engine = ConsensusEngine()
    height = 50
    block = empty_ledger_block(height=height)
    commitment = normalize_ledger_block(block, chain_id=engine.chain_id, height=height)
    block_id = f"h{height}-r0-P{engine.leader_for(height, 0)}-C{commitment['ledger_commitment']}"
    context = build_finality_certificate(
        chain_id=engine.chain_id,
        network_id=engine.network_id,
        height=height,
        round=0,
        block_id=block_id,
        validator_set=validators,
        votes=[],
        checkpoint_id=checkpoint["checkpoint_id"],
        ledger_commitment=commitment["ledger_commitment"],
        txs_root=commitment["txs_root"],
    )
    votes = [{
        "validator_id": f"val-{index + 1}",
        "signature_base64": base64.b64encode(
            keys[index].sign(vote_sign_bytes(context, f"val-{index + 1}"))
        ).decode("ascii"),
    } for index in range(2)]
    certificate = build_finality_certificate(
        chain_id=engine.chain_id,
        network_id=engine.network_id,
        height=height,
        round=0,
        block_id=block_id,
        validator_set=validators,
        votes=votes,
        checkpoint_id=checkpoint["checkpoint_id"],
        ledger_commitment=commitment["ledger_commitment"],
        txs_root=commitment["txs_root"],
    )
    assert engine._import_block_into_chain_sim_db(block) is True
    from backend.modules.chain_sim.chain_sim_ledger import replay_state_from_db
    replay_state_from_db()
    applied = engine.apply_verified_snapshot_finality(
        snapshot_summary={"snapshot_id": "ab" * 32, "ledger": {"height": height}},
        finality_certificate=certificate,
    )
    assert applied["applied"] is True
    assert applied["finalized_height"] == height
    assert engine.status()["partition_recovery"]["phase"] == "HEALTHY"

    tampered = dict(certificate)
    tampered["ledger_commitment"] = "ff" * 32
    with pytest.raises(ValueError):
        engine.apply_verified_snapshot_finality(
            snapshot_summary={"snapshot_id": "cd" * 32, "ledger": {"height": height + 1}},
            finality_certificate=tampered,
        )
