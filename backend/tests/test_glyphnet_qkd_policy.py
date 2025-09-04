# File: backend/tests/test_glyphnet_qkd_policy.py

import pytest
from backend.modules.glyphwave.qkd.glyphnet_qkd_policy import QKDPolicyEnforcer
from backend.modules.glyphwave.qkd_handshake import GKeyStore  # ✅ Correct import path
from backend.modules.glyphwave.qkd.qkd_policy_enforcer import QKDPolicyEnforcer

@pytest.fixture
def qkd_enforcer():
    return QKDPolicyEnforcer()

@pytest.fixture
def wave_packet_qkd_required():
    return {
        "sender_id": "agent_a",
        "recipient_id": "agent_b",
        "wave_id": "wave-999",
        "qkd_policy": {"require_qkd": True}
    }

@pytest.fixture
def wave_packet_qkd_not_required():
    return {
        "sender_id": "agent_a",
        "recipient_id": "agent_b",
        "wave_id": "wave-888",
        "qkd_policy": {"require_qkd": False}
    }

def test_policy_allows_when_not_required(qkd_enforcer, wave_packet_qkd_not_required):
    assert qkd_enforcer.enforce_policy(wave_packet_qkd_not_required) is True

def test_policy_blocks_without_valid_gkey(qkd_enforcer, wave_packet_qkd_required):
    # Ensure key store is clean
    store = GKeyStore
    store._key_pairs.clear()

    assert qkd_enforcer.enforce_policy(wave_packet_qkd_required) is False

def test_policy_allows_with_valid_gkey(qkd_enforcer, wave_packet_qkd_required):
    store = GKeyStore
    sender = wave_packet_qkd_required["sender_id"]
    recipient = wave_packet_qkd_required["recipient_id"]

    store.set_key_pair(sender, recipient, {
        "status": "verified",
        "public_key": "pubkey-sample",
        "collapse_hash": "abc123",
        "decoherence_fingerprint": "XYZ"
    })
    store.set_key_pair(recipient, sender, {
        "status": "verified",
        "public_key": "pubkey-sample",
        "collapse_hash": "abc123",
        "decoherence_fingerprint": "XYZ"
    })

    assert qkd_enforcer.enforce_policy(wave_packet_qkd_required) is True

def test_policy_blocks_if_gkey_not_verified(qkd_enforcer, wave_packet_qkd_required):
    store = GKeyStore
    sender = wave_packet_qkd_required["sender_id"]
    recipient = wave_packet_qkd_required["recipient_id"]

    store.set_key_pair(sender, recipient, {
        "status": "tampered",
        "public_key": "pubkey-sample",
        "collapse_hash": "abc123"
    })

    assert qkd_enforcer.enforce_policy(wave_packet_qkd_required) is False


@pytest.fixture(autouse=True)
def reset_gkey_store():
    GKeyStore.reset()
    yield
    GKeyStore.reset()


def test_detect_tampering_missing_keys():
    assert GKeyStore.detect_tampering("Alice", "Bob") is True


def test_detect_tampering_unverified_status():
    GKeyStore.set_key_pair("Alice", "Bob", {"status": "verified"})
    GKeyStore.set_key_pair("Bob", "Alice", {"status": "pending"})  # Not verified
    assert GKeyStore.detect_tampering("Alice", "Bob") is True


def test_detect_tampering_mismatch_collapse_hash():
    GKeyStore.set_key_pair("Alice", "Bob", {
        "status": "verified",
        "collapse_hash": "aaa"
    })
    GKeyStore.set_key_pair("Bob", "Alice", {
        "status": "verified",
        "collapse_hash": "bbb"
    })
    assert GKeyStore.detect_tampering("Alice", "Bob") is True


def test_detect_tampering_mismatch_decoherence_fingerprint():
    GKeyStore.set_key_pair("Alice", "Bob", {
        "status": "verified",
        "collapse_hash": "same",
        "decoherence_fingerprint": "fp1"
    })
    GKeyStore.set_key_pair("Bob", "Alice", {
        "status": "verified",
        "collapse_hash": "same",
        "decoherence_fingerprint": "fp2"
    })
    assert GKeyStore.detect_tampering("Alice", "Bob") is True


def test_detect_tampering_passes_all_checks():
    GKeyStore.set_key_pair("Alice", "Bob", {
        "status": "verified",
        "collapse_hash": "hash123",
        "decoherence_fingerprint": "fp"
    })
    GKeyStore.set_key_pair("Bob", "Alice", {
        "status": "verified",
        "collapse_hash": "hash123",
        "decoherence_fingerprint": "fp"
    })
    assert GKeyStore.detect_tampering("Alice", "Bob") is False

def test_enforce_policy_detects_tampering(monkeypatch):
    GKeyStore.set_key_pair("Alice", "Bob", {
        "status": "verified",
        "collapse_hash": "tampered_hash",
        "decoherence_fingerprint": "X"
    })
    GKeyStore.set_key_pair("Bob", "Alice", {
        "status": "verified",
        "collapse_hash": "original_hash",
        "decoherence_fingerprint": "Y"
    })

    enforcer = QKDPolicyEnforcer()
    result = enforcer.enforce_policy({
        "sender_id": "Alice",
        "recipient_id": "Bob",
        "wave_id": "wave-q1d",
        "qkd_policy": {"require_qkd": True}
    })

    # ✅ Tampering should cause enforcement to block
    assert result is False