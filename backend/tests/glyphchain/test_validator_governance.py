from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.consensus.finality_checkpoint import (
    CHECKPOINT_SCHEMA,
    FinalityCheckpointError,
    load_trusted_checkpoint_from_env,
    normalize_checkpoint,
)
from backend.modules.consensus.validator_governance import (
    FINALIZE_CONFIRMATION,
    PROPOSE_CONFIRMATION,
    ValidatorGovernanceError,
    ValidatorGovernanceStore,
    sign_approval,
    verify_transition_proof,
)


def _keys(count=4):
    return [Ed25519PrivateKey.generate() for _ in range(count)]


def _public(key):
    return base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii")


def _checkpoint(keys, *, epoch=0, effective_height=1, count=3):
    return normalize_checkpoint({
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": "glyphchain-main",
        "network_id": "production",
        "epoch": epoch,
        "effective_height": effective_height,
        "validator_set": [
            {"validator_id": f"val-{index + 1}", "power": 1, "public_key_base64": _public(keys[index])}
            for index in range(count)
        ],
    })


def test_admission_requires_current_quorum_and_emits_portable_transition_proof(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_VALIDATOR_CHANGE_MIN_LEAD_BLOCKS", "10")
    keys = _keys(); current = _checkpoint(keys); successor = _checkpoint(keys, epoch=1, effective_height=120, count=4)
    store = ValidatorGovernanceStore(tmp_path, current_checkpoint=current, clock_ms=lambda: 1000)
    state = store.propose(
        next_checkpoint=successor, action="admission", reason="increase resilience",
        governance_reference="board-42", operator_id="owner-1",
        confirmation=PROPOSE_CONFIRMATION, current_finalized_height=100,
    )
    proposal = state["proposal"]
    assert state["quorum_power"] == 2
    for index in range(2):
        state = store.add_approval(
            sign_approval(proposal, validator_id=f"val-{index + 1}", private_key=keys[index]),
            operator_id=f"operator-{index + 1}",
        )
    assert state["quorum_reached"] is True
    finalized = store.finalize(operator_id="owner-1", confirmation=FINALIZE_CONFIRMATION)
    proof = finalized["transition_proof"]
    result = verify_transition_proof(
        proof, expected_previous_checkpoint_id=current["checkpoint_id"],
        expected_next_checkpoint_id=successor["checkpoint_id"],
    )
    assert result["valid"] is True
    assert finalized["restart_required_at_height"] == 120
    assert ValidatorGovernanceStore(tmp_path, current_checkpoint=current).status()["status"] == "FINALIZED"


def test_peer_or_candidate_cannot_self_appoint_or_tamper_with_transition(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_VALIDATOR_CHANGE_MIN_LEAD_BLOCKS", "1")
    keys = _keys(); current = _checkpoint(keys); successor = _checkpoint(keys, epoch=1, effective_height=20, count=4)
    store = ValidatorGovernanceStore(tmp_path, current_checkpoint=current)
    state = store.propose(
        next_checkpoint=successor, action="admission", reason="capacity",
        governance_reference="board-7", operator_id="owner",
        confirmation=PROPOSE_CONFIRMATION, current_finalized_height=10,
    )
    candidate_approval = sign_approval(state["proposal"], validator_id="val-4", private_key=keys[3])
    with pytest.raises(ValidatorGovernanceError, match="signature"):
        store.add_approval(candidate_approval, operator_id="candidate")
    with pytest.raises(ValidatorGovernanceError, match="quorum"):
        store.finalize(operator_id="owner", confirmation=FINALIZE_CONFIRMATION)


def test_removal_proof_rejects_modified_successor_and_wrong_previous_pin(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_VALIDATOR_CHANGE_MIN_LEAD_BLOCKS", "1")
    keys = _keys(); current = _checkpoint(keys, count=4); successor = _checkpoint(keys, epoch=1, effective_height=20, count=3)
    store = ValidatorGovernanceStore(tmp_path, current_checkpoint=current)
    proposal = store.propose(
        next_checkpoint=successor, action="removal", reason="operator retirement",
        governance_reference="board-9", operator_id="owner",
        confirmation=PROPOSE_CONFIRMATION, current_finalized_height=10,
    )["proposal"]
    for index in range(3):
        store.add_approval(sign_approval(proposal, validator_id=f"val-{index + 1}", private_key=keys[index]), operator_id="owner")
    proof = store.finalize(operator_id="owner", confirmation=FINALIZE_CONFIRMATION)["transition_proof"]
    wrong_pin = verify_transition_proof(proof, expected_previous_checkpoint_id="wrong", expected_next_checkpoint_id=successor["checkpoint_id"])
    assert wrong_pin["valid"] is False
    tampered = json.loads(json.dumps(proof)); tampered["proposal"]["reason"] = "different"
    assert verify_transition_proof(
        tampered, expected_previous_checkpoint_id=current["checkpoint_id"], expected_next_checkpoint_id=successor["checkpoint_id"],
    )["valid"] is False


def test_compromised_validator_cannot_approve_emergency_removal_or_replacement(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_VALIDATOR_CHANGE_MIN_LEAD_BLOCKS", "1")
    keys = _keys(5)
    current = _checkpoint(keys, count=4)
    successor = _checkpoint(keys, epoch=1, effective_height=20, count=3)
    store = ValidatorGovernanceStore(tmp_path / "removal", current_checkpoint=current)
    proposal = store.propose(
        next_checkpoint=successor,
        action="emergency_removal",
        reason="retained incident evidence identifies validator val-4 as compromised",
        governance_reference="incident-GC-2026-001",
        operator_id="incident-commander",
        confirmation=PROPOSE_CONFIRMATION,
        current_finalized_height=10,
    )["proposal"]

    accused = sign_approval(proposal, validator_id="val-4", private_key=keys[3])
    with pytest.raises(ValidatorGovernanceError, match="being removed"):
        store.add_approval(accused, operator_id="accused-validator")

    for index in range(3):
        store.add_approval(
            sign_approval(proposal, validator_id=f"val-{index + 1}", private_key=keys[index]),
            operator_id=f"unaffected-operator-{index + 1}",
        )
    finalized = store.finalize(
        operator_id="incident-commander",
        confirmation=FINALIZE_CONFIRMATION,
    )
    proof = finalized["transition_proof"]
    assert verify_transition_proof(
        proof,
        expected_previous_checkpoint_id=current["checkpoint_id"],
        expected_next_checkpoint_id=successor["checkpoint_id"],
    )["valid"] is True
    assert finalized["proposal"]["governance_reference"] == "incident-GC-2026-001"
    assert ValidatorGovernanceStore(
        tmp_path / "removal", current_checkpoint=current
    ).status()["status"] == "FINALIZED"

    injected = json.loads(json.dumps(proof))
    injected["approvals"].append(accused)
    result = verify_transition_proof(
        injected,
        expected_previous_checkpoint_id=current["checkpoint_id"],
        expected_next_checkpoint_id=successor["checkpoint_id"],
    )
    assert result["valid"] is False
    assert "validator_transition_removed_validator_approval:val-4" in result["errors"]

    replacement = normalize_checkpoint({
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": "glyphchain-main",
        "network_id": "production",
        "epoch": 1,
        "effective_height": 20,
        "validator_set": [
            {"validator_id": f"val-{index + 1}", "power": 1, "public_key_base64": _public(keys[index])}
            for index in range(3)
        ] + [{"validator_id": "val-5", "power": 1, "public_key_base64": _public(keys[4])}],
    })
    replacement_store = ValidatorGovernanceStore(tmp_path / "replacement", current_checkpoint=current)
    replacement_proposal = replacement_store.propose(
        next_checkpoint=replacement,
        action="replacement",
        reason="replace compromised validator after separate candidate review",
        governance_reference="incident-GC-2026-001/replacement",
        operator_id="incident-commander",
        confirmation=PROPOSE_CONFIRMATION,
        current_finalized_height=10,
    )["proposal"]
    with pytest.raises(ValidatorGovernanceError, match="signature"):
        replacement_store.add_approval(
            sign_approval(replacement_proposal, validator_id="val-5", private_key=keys[4]),
            operator_id="joining-validator",
        )
    with pytest.raises(ValidatorGovernanceError, match="being removed"):
        replacement_store.add_approval(
            sign_approval(replacement_proposal, validator_id="val-4", private_key=keys[3]),
            operator_id="accused-validator",
        )


def test_production_checkpoint_loader_requires_quorum_governance_proof_for_later_epoch(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_VALIDATOR_CHANGE_MIN_LEAD_BLOCKS", "1")
    keys = _keys(); current = _checkpoint(keys); successor = _checkpoint(keys, epoch=1, effective_height=20, count=4)
    store = ValidatorGovernanceStore(tmp_path / "governance", current_checkpoint=current)
    proposal = store.propose(
        next_checkpoint=successor, action="admission", reason="resilience",
        governance_reference="board-10", operator_id="owner",
        confirmation=PROPOSE_CONFIRMATION, current_finalized_height=1,
    )["proposal"]
    for index in range(2):
        store.add_approval(sign_approval(proposal, validator_id=f"val-{index + 1}", private_key=keys[index]), operator_id="owner")
    proof = store.finalize(operator_id="owner", confirmation=FINALIZE_CONFIRMATION)["transition_proof"]
    checkpoint_path = tmp_path / "checkpoint.json"; checkpoint_path.write_text(json.dumps(successor))
    proof_path = tmp_path / "proof.json"; proof_path.write_text(json.dumps(proof))
    monkeypatch.setenv("GLYPHCHAIN_FINALITY_CHECKPOINT_PATH", str(checkpoint_path))
    monkeypatch.setenv("GLYPHCHAIN_TRUSTED_CHECKPOINT_ID", successor["checkpoint_id"])
    monkeypatch.setenv("GLYPHCHAIN_REQUIRE_VALIDATOR_GOVERNANCE", "1")
    with pytest.raises(FinalityCheckpointError, match="governance"):
        load_trusted_checkpoint_from_env()
    monkeypatch.setenv("GLYPHCHAIN_VALIDATOR_GOVERNANCE_PROOF_PATH", str(proof_path))
    monkeypatch.setenv("GLYPHCHAIN_PREVIOUS_TRUSTED_CHECKPOINT_ID", current["checkpoint_id"])
    assert load_trusted_checkpoint_from_env().checkpoint_id == successor["checkpoint_id"]
