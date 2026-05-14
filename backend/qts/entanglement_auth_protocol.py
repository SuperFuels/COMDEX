"""
🛰 Entanglement Authentication Protocol (EAP) - SRK-16 B2
Implements quantum-safe authentication for QGN node pairs.
Ensures both nodes share an entangled trust context derived from their QGN certificates.
"""

import hashlib
import time
from backend.qts.qgn_identity_registry import QuantumNodeCertificate


class EntanglementAuthProtocol:
    """
    Validates entangled link authenticity between two QGN nodes.
    Produces challenge-response tokens bound to node certificates.
    """

    def __init__(self):
        self._active_links = {}

    # ────────────────────────────────────────────────────────────────
    def initiate_handshake(self, initiator_cert: QuantumNodeCertificate, responder_cert: QuantumNodeCertificate) -> str:
        """Generate a challenge for an entangled authentication session."""
        challenge_seed = f"{initiator_cert.node_id}:{responder_cert.node_id}:{time.time_ns()}"
        challenge = hashlib.sha3_512(challenge_seed.encode()).hexdigest()[:32]
        self._active_links[(initiator_cert.node_id, responder_cert.node_id)] = {
            "challenge": challenge,
            "timestamp": time.time(),
        }
        return challenge

    # ────────────────────────────────────────────────────────────────
    def respond_handshake(self, responder_cert: QuantumNodeCertificate, challenge: str) -> str:
        """Respond to challenge using responder's certificate signature."""
        base = f"{responder_cert.signature}:{challenge}"
        response = hashlib.sha3_512(base.encode()).hexdigest()
        return response

    # ────────────────────────────────────────────────────────────────
    def verify(
        self,
        initiator_cert: QuantumNodeCertificate,
        responder_cert: QuantumNodeCertificate,
        challenge: str,
        response: str,
    ) -> bool:
        """Validate entanglement handshake authenticity."""
        # Re-derive expected hash baseline
        base = f"{responder_cert.signature}:{challenge}"
        expect_prefix = hashlib.sha3_512(base.encode()).hexdigest()[:32]

        match = response.startswith(expect_prefix)
        link_key = (initiator_cert.node_id, responder_cert.node_id)
        self._active_links.pop(link_key, None)

        if match:
            print(f"[EAP] ✅ Verified entanglement link between {initiator_cert.node_id} ↔ {responder_cert.node_id}")
        else:
            print(f"[EAP] ❌ Verification failed for {initiator_cert.node_id} ↔ {responder_cert.node_id}")

        return match