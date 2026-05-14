import pytest
from unittest.mock import patch, MagicMock
from backend.modules.glyphwave.qkd.gkey_encryptor import GWaveEncryptor
from backend.modules.glyphwave.qkd_handshake import GKeyStore
from backend.modules.glyphnet.glyph_transmitter import push_wave
from backend.modules.exceptions.tampered_payload import TamperedPayloadError


def test_push_wave_with_qkd_retry(monkeypatch):
    sender_id = "agent.alice"
    recipient_id = "agent.bob"

    payload = {
        "message": "secure transmission",
        "symbols": ["⧖", "↔", "⊕"],
        "qkd_policy": {
            "require_qkd": True
        }
    }

    wave_packet = {
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "payload": payload
    }

    # Simulate initial encryption with valid GKey
    valid_gkey = {
        "collapse_hash": "abc123",
        "status": "verified"
    }

    encrypted_blob = GWaveEncryptor(valid_gkey).encrypt_payload(payload)

    # Patch get_key_pair to return valid, then updated on retry
    call_count = {"count": 0}

    def mock_get_key_pair(s, r):
        if call_count["count"] == 0:
            call_count["count"] += 1
            return valid_gkey  # used for encryption
        return valid_gkey  # re-used on retry

    monkeypatch.setattr(GKeyStore, "get_key_pair", staticmethod(mock_get_key_pair))

    # Patch decrypt to raise TamperedPayloadError first, succeed second
    decrypt_mock = MagicMock()
    decrypt_mock.side_effect = [TamperedPayloadError("tampered"), {"message": "secure transmission"}]

    monkeypatch.setattr(GWaveEncryptor, "decrypt_payload", decrypt_mock)

    # Patch renegotiation to simulate key refresh
    monkeypatch.setattr(GKeyStore, "renegotiate", staticmethod(lambda s, r: True))

    result = push_wave(wave_packet)

    assert result["status"] == "ok"
    assert result["qkd_used"] is True
    assert "transmitted_payload" in result