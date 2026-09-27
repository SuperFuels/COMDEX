from pathlib import Path


def test_standalone_legal_proof_verifier_is_local_only():
    path = Path("backend/modules/aion_business/static/tessaris-proof-verifier.html")
    source = path.read_text(encoding="utf-8")

    assert "Document proof verifier" in source
    assert ".tessaris-proof" in source
    assert "not uploaded or transmitted" in source
    assert "crypto.subtle.verify" in source
    assert "chain_context" in source
    assert "Transaction payload binding" in source
    assert "Private signer commitments" in source
    assert "Quorum finality" in source
    assert "validator_set_root" in source
    assert "Public validator checkpoint" in source
    assert "Independently obtained checkpoint ID" in source
    assert "INDEPENDENT PIN NOT SUPPLIED" in source
    assert "pin!==cpId" in source
    assert "checkpointPinInput.value" in source
    assert "receipt is never allowed to appoint its own trust anchor" in source
    assert "SIGNATURES VALID · TRUST ANCHOR NOT SUPPLIED" in source
    assert "chain.trusted_validator_set_root!==root" not in source
    assert "GLYPHCHAIN_FINALITY_PRECOMMIT_V1" in source
    assert "evidence-certificate.json" in source
    assert "DOCUMENT_PROOF_V1" in source
    assert "leaf:" in source
    assert "node:" in source
    assert "fetch(" not in source
    assert "http://" not in source
    assert "https://" not in source
    assert "Photon" not in source
