from pathlib import Path

DOC = Path("docs/rfc/aion_gateway_normalized_inbound_intent_lock.tex")


def _text() -> str:
    return DOC.read_text()


def test_gateway_lock_doc_exists_and_has_lock_id():
    text = _text()
    assert "AION-GATEWAY-NORMALIZED-INBOUND-INTENT-v0.1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_gateway_lock_doc_is_backend_only_and_dry_run_only():
    text = _text()
    assert "backend-only" in text
    assert "dry-run-only" in text
    assert "MUST NOT add public routes" in text
    assert "MUST NOT create a real fulfilment job" in text or "MUST NOT create a real fulfilment job" in text


def test_gateway_lock_doc_names_core_contracts():
    text = _text()
    assert "NormalizedInboundIntent" in text
    assert "FulfilmentJobPreview" in text
    assert "machine-readable preview trace" in text


def test_gateway_lock_doc_supports_only_two_v0_channels():
    text = _text()
    assert "legacy\\_web\\_form" in text
    assert "agent\\_protocol" in text
    assert "website\\_button" in text
    assert "embedded\\_chat" in text
    assert "reserved but not live in v0" in text


def test_gateway_lock_doc_keeps_raw_and_normalized_payload_separate():
    text = _text()
    assert "raw\\_payload" in text
    assert "original untrusted input" in text
    assert "normalized\\_payload" in text
    assert "cleaned typed operational intent" in text


def test_gateway_lock_doc_locks_hash_rules():
    text = _text()
    assert "hashlib.sha256()" in text
    assert "sort_keys=True" in text
    assert "separators=(',', ':')" in text
    assert "business\\_id.lower()" in text
    assert "source\\_channel.lower()" in text
    assert "intent\\_type.lower()" in text
    assert "MUST NOT include \\texttt{raw\\_payload}" in text
    assert "MUST NOT grant permission or trigger execution" in text


def test_gateway_lock_doc_locks_safety_guard():
    text = _text()
    assert "@enforce\\_dry\\_run\\_only" in text
    assert "RuntimeError" in text
    assert "MUST NOT" in text
    assert "Call providers" in text
    assert "Grant permissions" in text


def test_gateway_lock_doc_records_validation_commands():
    text = _text()
    assert "test_aion_gateway_normalized_inbound_intent.py" in text
    assert "10 passed" in text
    assert "python -m compileall backend/modules/aion_gateway" in text
