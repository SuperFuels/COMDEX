"""
🌐 Tessaris QTS API Gateway — SRK-16 B5
Provides lightweight REST + GraphQL interfaces for QTS operations.
"""

from fastapi import FastAPI, HTTPException
from backend.qts.qgn_identity_registry import QGNIdentityRegistry
from backend.qts.entanglement_auth_protocol import EntanglementAuthProtocol

app = FastAPI(title="Tessaris QTS API Gateway")
_registry = QGNIdentityRegistry()
_eap = EntanglementAuthProtocol()

@app.post("/qnc/issue")
async def issue_qnc(node_id: str, qkd_public_key: str, coherence_fingerprint: str):
    cert = _registry.issue_certificate(node_id, qkd_public_key, coherence_fingerprint)
    return cert.__dict__

@app.post("/qnc/verify")
async def verify_qnc(cert: dict):
    from backend.qts.qgn_identity_registry import QuantumNodeCertificate
    obj = QuantumNodeCertificate(**cert)
    return {"valid": _registry.verify_certificate(obj)}

@app.post("/eap/handshake")
async def eap_handshake(a_cert: dict, b_cert: dict):
    from backend.qts.qgn_identity_registry import QuantumNodeCertificate
    a, b = QuantumNodeCertificate(**a_cert), QuantumNodeCertificate(**b_cert)
    token = _eap.initiate_handshake(a, b)
    return {"challenge": token}