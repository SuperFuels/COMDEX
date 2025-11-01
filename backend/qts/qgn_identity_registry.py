"""
🛰 QGN-Identity Registry - SRK-16 Task B1
Manages quantum node identity certificates (QNCs) for Tessaris QGN nodes.
Each QNC binds a node's coherence fingerprint, QKD keypair, and signature metadata.
"""

import time, hashlib, json
from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class QuantumNodeCertificate:
    node_id: str
    coherence_fingerprint: str
    qkd_public_key: str
    issued_at: float
    signature: str

class QGNIdentityRegistry:
    def __init__(self):
        self._registry: Dict[str, QuantumNodeCertificate] = {}

    def issue_certificate(self, node_id: str, qkd_public_key: str, coherence_fingerprint: str) -> QuantumNodeCertificate:
        payload = f"{node_id}:{qkd_public_key}:{coherence_fingerprint}:{time.time()}"
        signature = hashlib.sha3_256(payload.encode()).hexdigest()
        cert = QuantumNodeCertificate(
            node_id=node_id,
            qkd_public_key=qkd_public_key,
            coherence_fingerprint=coherence_fingerprint,
            issued_at=time.time(),
            signature=signature,
        )
        self._registry[node_id] = cert
        return cert

    def verify_certificate(self, cert: QuantumNodeCertificate) -> bool:
        payload = f"{cert.node_id}:{cert.qkd_public_key}:{cert.coherence_fingerprint}:{cert.issued_at}"
        expected_sig = hashlib.sha3_256(payload.encode()).hexdigest()
        return expected_sig == cert.signature

    def export_registry(self) -> str:
        """Export all active QNCs as JSON."""
        return json.dumps({nid: asdict(c) for nid, c in self._registry.items()}, indent=2)