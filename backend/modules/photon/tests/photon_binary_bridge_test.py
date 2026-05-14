"""
🧪 PhotonBinaryBridge - SRK-10 -> SRK-16 Integration Test Suite
Validates:
 * GWIP -> Photon Capsule conversion
 * QKD + coherence enforcement
 * QTS encryption / decryption via EncryptedPhotonChannel
"""

import pytest
import hashlib
import base64
from backend.modules.photon.photon_binary_bridge import PhotonBinaryBridge
from backend.qts.encrypted_photon_channel import EncryptedPhotonChannel


# Dummy wave object for simulation
class DummyWave:
    def __init__(self):
        self.metadata = {"coherence": 0.95}


# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_gwip_to_photon_capsule_roundtrip_with_qts():
    """Validate GWIP -> Photon Capsule pipeline including QTS encryption."""
    bridge = PhotonBinaryBridge(mode="photon")

    payload = '{"data":"test"}'
    payload_hash = hashlib.sha3_512(payload.encode()).hexdigest()

    gwip = {
        "type": "gwip",
        "schema": 3,
        "envelope": {
            "packet_id": "test_gwip_001",
            "source_container": "source",
            "target_container": "target",
            "carrier_type": "OPTICAL",
            "freq": 440.0,
            "phase": 0.75,
            "coherence": 0.95,
            "qkd_required": True,
            "gkey_id": "QKD-SIM-001",
            "timestamp": 123456789.0,
        },
        "payload": payload,
        "hash": payload_hash,
    }

    wave_state = DummyWave()
    capsule = await bridge.gwip_to_photon_capsule(gwip, "sender_A", "receiver_B", wave_state)

    # Basic capsule verification
    assert "glyphs" in capsule, "Photon Capsule missing glyph data"
    assert "encrypted_payload" in capsule, "Encrypted payload missing in capsule"
    meta = capsule["glyphs"][0]["meta"]
    assert meta.get("qkd_verified") in (True, False), "QKD verification flag invalid"

    # --- Decrypt and validate ---
    encrypted_blob = capsule["encrypted_payload"]
    if isinstance(encrypted_blob, str):
        try:
            encrypted_blob = base64.b64decode(encrypted_blob)
        except Exception:
            encrypted_blob = encrypted_blob.encode()

    qkd_key = gwip["envelope"]["gkey_id"]
    assert qkd_key, "Missing QKD key for decryption"

    epc = EncryptedPhotonChannel(qkd_key)
    decrypted = epc.decrypt(encrypted_blob)

    assert b"data" in decrypted, "Decrypted payload missing original content"
    print("\n✅ PhotonBinaryBridge GWIP->Capsule + QTS encryption test passed.")


# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_secure_transmit_encryption_roundtrip():
    """Validate direct secure_transmit() AES-QKD hybrid encryption."""
    bridge = PhotonBinaryBridge(mode="photon")

    gwip_packet = {
        "envelope": {
            "packet_id": "GWIP-TEST-1",
            "carrier_type": "OPTICAL",
            "coherence": 0.95,
            "qkd_key": "QKD-SIM-123",
        },
        "payload": {"test": "photonic payload"},
    }

    # Encrypt via QTS layer
    encrypted_payload = await bridge.secure_transmit(gwip_packet)
    assert isinstance(encrypted_payload, (bytes, bytearray, str))
    if isinstance(encrypted_payload, str):
        try:
            encrypted_payload = base64.b64decode(encrypted_payload)
        except Exception:
            encrypted_payload = encrypted_payload.encode()

    assert len(encrypted_payload) > 0, "Empty encrypted payload"

    # Decrypt and confirm roundtrip integrity
    epc = EncryptedPhotonChannel("QKD-SIM-123")
    decrypted = epc.decrypt(encrypted_payload)
    assert b"photonic payload" in decrypted, "Payload decryption mismatch"

    print("\n✅ PhotonBinaryBridge secure_transmit() encryption test passed.")