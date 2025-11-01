"""
🧪 QTS Handshake Flow Test - SRK-16 Integration (B1 -> B2 -> B3)
Validates end-to-end quantum node authentication and encrypted photon transmission.
"""

import pytest
import asyncio
from backend.qts.qgn_identity_registry import QGNIdentityRegistry, QuantumNodeCertificate
from backend.qts.entanglement_auth_protocol import EntanglementAuthProtocol
from backend.qts.encrypted_photon_channel import EncryptedPhotonChannel
from backend.qts.quantum_policy_engine import QuantumPolicyEngine
from backend.modules.photon.photon_binary_bridge import PhotonBinaryBridge


@pytest.mark.asyncio
async def test_qts_handshake_and_encryption_flow():
    # ───────────────────────────────────────────────
    # 1️⃣ Issue Quantum Node Certificates (B1)
    # ----------------------------------------------------------------
    registry = QGNIdentityRegistry()
    sender_cert = registry.issue_certificate("NODE-A", "PUB_A123", "CFP-001")
    receiver_cert = registry.issue_certificate("NODE-B", "PUB_B456", "CFP-002")

    assert sender_cert.node_id == "NODE-A"
    assert receiver_cert.node_id == "NODE-B"

    # ───────────────────────────────────────────────
    # 2️⃣ Entanglement Authentication Protocol (B2)
    # ----------------------------------------------------------------
    eap = EntanglementAuthProtocol()
    challenge = eap.initiate_handshake(sender_cert, receiver_cert)
    assert isinstance(challenge, str) and len(challenge) > 0

    response = eap.respond_handshake(receiver_cert, challenge)
    verified = eap.verify(sender_cert, receiver_cert, challenge, response)
    assert verified, "EAP verification failed - entanglement link not authenticated"

    # ───────────────────────────────────────────────
    # 3️⃣ Encrypted Photon Channel (B3)
    # ----------------------------------------------------------------
    qkd_key = challenge[:32]  # use handshake token segment as simulated QKD key
    epc = EncryptedPhotonChannel(qkd_key)

    original_data = b"Tessaris: Quantum Transport Test"
    encrypted = epc.encrypt(original_data)
    decrypted = epc.decrypt(encrypted)
    assert decrypted == original_data, "EPC-1 decryption mismatch"

    # ───────────────────────────────────────────────
    # 4️⃣ PhotonBinaryBridge Secure Transmission (SRK-16 Integrated)
    # ----------------------------------------------------------------
    bridge = PhotonBinaryBridge(mode="binary")  # use binary mode for test isolation

    gwip_packet = {
        "meta": {"carrier_type": "OPTICAL", "coherence": 0.9, "qkd_key": qkd_key},
        "envelope": {"packet_id": "GWIP-001", "coherence": 0.9, "carrier_type": "OPTICAL"},
        "payload": {"data": "Quantum secured payload"},
    }

    encrypted_bridge_payload = await bridge.secure_transmit(gwip_packet)
    assert isinstance(encrypted_bridge_payload, (bytes, bytearray))
    assert len(encrypted_bridge_payload) > 0

    # Try decryption using the same QKD key to verify encryption consistency
    decrypted_bridge = epc.decrypt(encrypted_bridge_payload)
    assert b"Quantum secured payload" in decrypted_bridge, "Bridge encryption failed verification"

    # ───────────────────────────────────────────────
    # 5️⃣ Policy Enforcement Validation
    # ----------------------------------------------------------------
    qpe = QuantumPolicyEngine()
    assert qpe.enforce(gwip_packet["meta"]), "QuantumPolicyEngine rejected valid packet"

    # Final Success Log
    print("\n✅ SRK-16 End-to-End QTS Handshake + Encryption verified successfully.")