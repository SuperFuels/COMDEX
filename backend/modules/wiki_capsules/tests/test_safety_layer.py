# ────────────────────────────────────────────────────────────────
# File: backend/modules/wiki_capsules/security/test_safety_layer.py
# ────────────────────────────────────────────────────────────────
import os
import hashlib
import tempfile
from backend.modules.wiki_capsules.security.safety_layer import SafetyLayer

def make_capsule(content="test", signer="Tessaris-Core"):
    return {
        "signed_by": signer,
        "checksum": hashlib.sha3_256(content.encode()).hexdigest(),
        "content": content,
        "timestamp": "2025-10-25T00:00:00Z",
    }

def test_signature_verification_passes():
    sl = SafetyLayer()
    capsule = make_capsule("data123")
    assert sl.verify_signature(capsule) is True

def test_signature_verification_fails_wrong_checksum():
    sl = SafetyLayer()
    capsule = make_capsule("data123")
    capsule["checksum"] = "0000"
    assert sl.verify_signature(capsule) is False

def test_whitelist_enforcement():
    sl = SafetyLayer()
    assert sl.is_whitelisted("Tessaris-Core>AI") is True
    assert sl.is_whitelisted("MaliciousEntity>Test") is False

def test_sandbox_enforcement_readonly(tmp_path):
    f = tmp_path / "readonly.wiki.phn"
    f.write_text("static capsule")
    f.chmod(0o444)  # read-only
    sl = SafetyLayer()
    assert sl.enforce_sandbox(str(f), ".wiki.phn") is True

def test_sandbox_enforcement_block_exec(tmp_path):
    f = tmp_path / "restricted.ptn"
    f.write_text("bad = exec('rm -rf /')")
    sl = SafetyLayer()
    assert sl.enforce_sandbox(str(f), ".ptn") is False

def test_audit_event(tmp_path):
    log_path = tmp_path / "audit.log"
    sl = SafetyLayer(audit_log_path=str(log_path))
    entry = sl.audit_event("SQI_UPDATE", "Lexicon>Orange", sqi_delta=+0.12)
    assert "Lexicon>Orange" in entry["capsule"]
    assert log_path.exists()