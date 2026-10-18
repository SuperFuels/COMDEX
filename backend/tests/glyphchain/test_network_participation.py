from __future__ import annotations

import json

import pytest

from backend.modules.p2p.network_participation import (
    NetworkParticipationError,
    NetworkParticipationStore,
    participation_from_env,
)


def test_default_install_is_light_and_cannot_relay_or_vote(tmp_path):
    status = NetworkParticipationStore(tmp_path).status()
    assert status["role"] == "light"
    assert status["opted_in"] is False
    assert status["capabilities"]["verify_proofs"] is True
    assert status["capabilities"]["relay_messages"] is False
    assert status["capabilities"]["vote"] is False


def test_relay_requires_exact_confirmation_and_connectivity_acknowledgement(tmp_path):
    store = NetworkParticipationStore(tmp_path)
    with pytest.raises(NetworkParticipationError, match="explicit_confirmation"):
        store.configure(role="relay", operator_id="owner", confirmation="yes")
    with pytest.raises(NetworkParticipationError, match="connectivity_acknowledgement"):
        store.configure(
            role="relay", operator_id="owner", confirmation="ENABLE GLYPHCHAIN RELAY",
        )
    configured = store.configure(
        role="relay", operator_id="owner", confirmation="ENABLE GLYPHCHAIN RELAY",
        public_connectivity_acknowledged=True,
    )
    assert configured["role"] == "relay"
    assert configured["capabilities"]["relay_messages"] is True
    assert configured["capabilities"]["vote"] is False
    assert store.verify_audit_chain() is True


def test_validator_requires_governance_checkpoint_availability_and_key_custody(tmp_path):
    store = NetworkParticipationStore(tmp_path)
    base = {
        "role": "validator",
        "operator_id": "owner",
        "confirmation": "ENABLE GLYPHCHAIN VALIDATOR",
        "public_connectivity_acknowledged": True,
    }
    with pytest.raises(NetworkParticipationError, match="availability"):
        store.configure(**base)
    with pytest.raises(NetworkParticipationError, match="key_custody"):
        store.configure(**base, availability_acknowledged=True)
    with pytest.raises(NetworkParticipationError, match="governance"):
        store.configure(**base, availability_acknowledged=True, key_custody_acknowledged=True)
    configured = store.configure(
        **base,
        availability_acknowledged=True,
        key_custody_acknowledged=True,
        governance_approval_id="admission-42",
        validator_set_checkpoint_id="checkpoint-42",
    )
    assert configured["role"] == "validator"
    assert configured["capabilities"]["vote"] is True
    disabled = store.disable_elevated_participation(operator_id="owner", reason="device retired")
    assert disabled["role"] == "light"
    assert disabled["opted_in"] is False
    assert store.verify_audit_chain() is True


def test_enforced_runtime_ignores_validator_environment_without_admin_record(monkeypatch, tmp_path):
    monkeypatch.setenv("GLYPHCHAIN_ENFORCE_EXPLICIT_PARTICIPATION", "1")
    monkeypatch.setenv("GLYPHCHAIN_PARTICIPATION_DIR", str(tmp_path))
    monkeypatch.setenv("GLYPHCHAIN_SELF_VAL_ID", "unexpected-validator")
    state = participation_from_env()
    assert state["enforced"] is True
    assert state["role"] == "light"
    assert state["capabilities"]["vote"] is False

    monkeypatch.setenv("GLYPHCHAIN_STATE_DIR", str(tmp_path / "consensus"))
    monkeypatch.setenv("GLYPHCHAIN_VALIDATORS", "unexpected-validator:1,other:1")
    from backend.modules.consensus.engine import ConsensusEngine
    engine = ConsensusEngine()
    assert engine.self_val_id == ""
    assert engine.status()["network_participation"]["role"] == "light"


def test_tampered_role_state_is_rejected(tmp_path):
    store = NetworkParticipationStore(tmp_path)
    store.configure(role="light", operator_id="owner")
    state = json.loads(store.path.read_text(encoding="utf-8"))
    state["role"] = "validator"
    state["opted_in"] = False
    store.path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(NetworkParticipationError, match="not_approved"):
        store.status()
