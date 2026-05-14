import pytest
from unittest.mock import patch

from backend.modules.glyphnet.glyph_transmitter import push_wave
from backend.modules.glyphwave.qkd_handshake import GKeyStore
from backend.modules.glyphwave.qkd.gkey_encryptor import GWaveEncryptor

@pytest.fixture
def sender():
    return "node-A"

@pytest.fixture
def recipient():
    return "node-B"

@pytest.fixture
def gkey_pair():
    return {
        "collapse_hash": "abc123",
        "decoherence_fingerprint": "XYZ789",
        "public_key": "pubkey-A",
        "status": "verified"
    }

@pytest.fixture(autouse=True)
def setup_gkey_store(sender, recipient, gkey_pair):
    store = GKeyStore()
    store.set_key_pair(sender, recipient, gkey_pair)
    store.set_key_pair(recipient, sender, gkey_pair)

@pytest.fixture
def raw_payload():
    return {
        "symbols": ["⊕", "↔", "∑"],
        "channel": "audio",
        "qkd_policy": {
            "require_qkd": True
        }
    }

def test_push_wave_with_qkd_encryption(sender, recipient, raw_payload):
    wave_packet = {
        "sender_id": sender,
        "recipient_id": recipient,
        "payload": raw_payload,
        "channel": "audio"
    }

    result = push_wave(wave_packet)

    assert result["status"] == "ok"
    assert result["qkd_used"] is True

    encrypted = result["transmitted_payload"]
    assert encrypted.get("qkd_encrypted") is True

    # Decrypt and validate payload
    store = GKeyStore()
    gkey = store.get_key_pair(sender, recipient)
    decryptor = GWaveEncryptor(gkey)
    decrypted = decryptor.decrypt_payload(encrypted)

    assert decrypted["symbols"] == ["⊕", "↔", "∑"]
    assert decrypted["channel"] == "audio"
    assert decrypted["qkd_policy"]["require_qkd"] is True

def test_push_wave_without_qkd(sender, recipient):
    raw_payload = {
        "symbols": ["Δ", "Ψ"],
        "channel": "led",
        "qkd_policy": {
            "require_qkd": False
        }
    }

    wave_packet = {
        "sender_id": sender,
        "recipient_id": recipient,
        "payload": raw_payload,
        "channel": "led"
    }

    result = push_wave(wave_packet)
    assert result["status"] == "ok"
    assert "qkd_encrypted" not in wave_packet  # Should not be marked
    assert wave_packet["payload"] == raw_payload