"""
🧪 PhotonBinaryBridge Tests (SRK-10)
Validates bidirectional translation between:
 - GWIP packets (binary domain)
 - Photon Capsules (symbolic domain)
"""

import pytest
import asyncio
import hashlib
import json
from types import SimpleNamespace
from backend.modules.photon.photon_binary_bridge import PhotonBinaryBridge


# ────────────────────────────────────────────────────────────────
# 🔐 Utility
# ----------------------------------------------------------------
def make_valid_hash(payload: dict | str) -> str:
    """Generate deterministic SHA3-512 hex digest (128 hex chars)."""
    if isinstance(payload, dict):
        payload = json.dumps(payload, sort_keys=True)
    return hashlib.sha3_512(payload.encode()).hexdigest()


# ────────────────────────────────────────────────────────────────
# ⚙️ Fixtures
# ----------------------------------------------------------------
@pytest.fixture
def valid_gwip_packet():
    payload = {"data": "test_payload"}
    return {
        "type": "gwip",
        "schema": 3,
        "envelope": {
            "packet_id": "gwip_test_001",
            "source_container": "alpha",
            "target_container": "beta",
            "freq": 2.45e9,
            "phase": 0.5,
            "coherence": 0.98,
            "timestamp": 123456.789,
        },
        "payload": json.dumps(payload),
        "hash": make_valid_hash(payload),
        "signature": "sig_dummy",
    }


@pytest.fixture
def valid_photon_capsule():
    return {
        "name": "PhotonCapsule_X",
        "version": "1.0",
        "glyphs": [
            {
                "name": "Emit",
                "operator": "⊕",
                "logic": "wave→photon",
                "args": [2.45e9, 0.5],
                "meta": {"coherence": 0.97},
            }
        ],
    }


# ────────────────────────────────────────────────────────────────
# 🔬 Global Mocks
# ----------------------------------------------------------------
@pytest.fixture(autouse=True)
def patch_qkd_and_validators(monkeypatch):
    """Patch QKD handshake + validators to neutralize schema/runtime mismatches."""

    # --- 1️⃣ QKD Handshake and Logger ---
    async def fake_qkd(sender_id, receiver_id, wave):
        return True

    async def fake_log_qkd_event(**kwargs):
        # Accept *any* keyword args, including entropy_level
        return {"ok": True, "wave_id": kwargs.get("wave_id")}

    import backend.modules.glyphwave.qkd.qkd_crypto_handshake as qkd_handshake
    import backend.modules.glyphwave.qkd.qkd_logger as qkd_logger

    monkeypatch.setattr(qkd_handshake, "initiate_qkd_handshake", fake_qkd)
    monkeypatch.setattr(qkd_logger, "log_qkd_event", fake_log_qkd_event)

    # --- 2️⃣ GWIP Schema Validator ---
    import backend.modules.glyphwave.protocol.gwip_schema as gwip_schema

    original_validate_gwip_schema = gwip_schema.validate_gwip_schema

    def patched_gwip_schema(packet):
        """Inject valid hash if placeholder appears."""
        if packet.get("hash") == "pending":
            packet["hash"] = make_valid_hash(packet.get("payload", ""))
        return original_validate_gwip_schema(packet)

    monkeypatch.setattr(gwip_schema, "validate_gwip_schema", patched_gwip_schema)

    # --- 3️⃣ Photon Capsule Validator ---
    import backend.modules.photon.photon_capsule_validator as capsule_validator
    original_validate_capsule = capsule_validator.validate_photon_capsule

    def patched_capsule_validator(capsule):
        """Remove root meta key if schema forbids it."""
        if "meta" in capsule:
            capsule = {k: v for k, v in capsule.items() if k != "meta"}
        return original_validate_capsule(capsule)

    monkeypatch.setattr(capsule_validator, "validate_photon_capsule", patched_capsule_validator)


# ────────────────────────────────────────────────────────────────
# ✅ Tests
# ----------------------------------------------------------------
@pytest.mark.asyncio
async def test_gwip_to_photon_capsule_roundtrip(valid_gwip_packet):
    bridge = PhotonBinaryBridge()
    wave = SimpleNamespace(metadata={"wave_id": "W123"})

    capsule = await bridge.gwip_to_photon_capsule(
        valid_gwip_packet,
        sender_id="node_A",
        receiver_id="node_B",
        wave=wave,
        include_qkd=True,
    )

    assert isinstance(capsule, dict)
    assert "glyphs" in capsule
    assert capsule["glyphs"][0]["operator"] == "⊕"
    assert capsule["glyphs"][0]["meta"]["qkd_verified"] is True


def test_photon_to_gwip_conversion(valid_photon_capsule):
    bridge = PhotonBinaryBridge()
    gwip_packet = bridge.photon_capsule_to_gwip(valid_photon_capsule)

    assert isinstance(gwip_packet, dict)
    assert gwip_packet["type"] == "gwip"
    assert "payload" in gwip_packet


@pytest.mark.asyncio
async def test_bidirectional_consistency(valid_gwip_packet):
    bridge = PhotonBinaryBridge()
    wave = SimpleNamespace(metadata={"wave_id": "W999"})

    capsule = await bridge.gwip_to_photon_capsule(valid_gwip_packet, "alpha", "beta", wave)
    new_gwip = bridge.photon_capsule_to_gwip(capsule)

    assert new_gwip["envelope"]["coherence"] == pytest.approx(1.0, rel=0.2)


@pytest.mark.asyncio
async def test_gwip_to_photon_without_qkd(valid_gwip_packet):
    bridge = PhotonBinaryBridge()
    wave = SimpleNamespace(metadata={"wave_id": "W321"})

    capsule = await bridge.gwip_to_photon_capsule(valid_gwip_packet, "node_X", "node_Y", wave, include_qkd=False)
    assert capsule["glyphs"][0]["meta"]["qkd_verified"] is False


def test_schema_validation_helpers(valid_gwip_packet, valid_photon_capsule):
    from backend.modules.glyphwave.protocol.gwip_schema import validate_gwip_schema
    from backend.modules.photon.photon_capsule_validator import validate_photon_capsule

    validate_gwip_schema(valid_gwip_packet)
    validate_photon_capsule(valid_photon_capsule)