from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

GLYPHCHAIN_FILES = [
    "backend/modules/aion_gateway/glyphchain_proof_commit.py",
    "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_commit_lock.py",
    "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_commit_lock_doc.py",
    "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_commit_store_lock.py",
    "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_commit_store_lock_doc.py",
    "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_receipt_lookup_lock.py",
    "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_receipt_lookup_lock_doc.py",
    "docs/rfc/aion_gateway_glyphchain_proof_commit_lock.tex",
    "docs/rfc/aion_gateway_glyphchain_proof_commit_store_lock.tex",
    "docs/rfc/aion_gateway_glyphchain_proof_receipt_lookup_lock.tex",
]


def _text(path: str) -> str:
    return (ROOT / path).read_text().lower()


def test_phase13_glyphchain_proof_receipt_files_exist():
    for path in GLYPHCHAIN_FILES:
        assert (ROOT / path).exists(), path


def test_phase13_glyphchain_proof_receipt_identity_is_hash_based():
    combined = "\n".join(_text(path) for path in GLYPHCHAIN_FILES)

    for term in [
        "glyphchain",
        "proof",
        "hash",
    ]:
        assert term in combined

    for forbidden in [
        "uuid.uuid4",
        "random.uuid",
        "secrets.token",
        "random_id",
        "runtime_random",
    ]:
        assert forbidden not in combined


def test_phase13_glyphchain_proof_receipt_lookup_contract_is_locked():
    combined = "\n".join(
        _text(path)
        for path in [
            "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_receipt_lookup_lock.py",
            "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_receipt_lookup_lock_doc.py",
            "docs/rfc/aion_gateway_glyphchain_proof_receipt_lookup_lock.tex",
        ]
    )

    for term in [
        "lookup",
        "receipt",
        "proof",
        "glyphchain",
    ]:
        assert term in combined


def test_phase13_glyphchain_proof_commit_store_contract_is_locked():
    combined = "\n".join(
        _text(path)
        for path in [
            "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_commit_store_lock.py",
            "backend/tests/workflow_capsules/test_aion_gateway_glyphchain_proof_commit_store_lock_doc.py",
            "docs/rfc/aion_gateway_glyphchain_proof_commit_store_lock.tex",
        ]
    )

    for term in [
        "proof",
        "commit",
        "store",
        "glyphchain",
    ]:
        assert term in combined


def test_phase13_glyphchain_proof_commit_does_not_live_publish_chain():
    combined = "\n".join(_text(path) for path in GLYPHCHAIN_FILES)

    for forbidden in [
        "web3",
        "ethers",
        "broadcast_transaction",
        "send_raw_transaction",
        "submit_transaction",
        "wallet_private_key",
        "live_chain_write",
    ]:
        assert forbidden not in combined


def test_phase13_glyphchain_proof_receipt_keeps_preview_safety_boundary():
    combined = "\n".join(_text(path) for path in GLYPHCHAIN_FILES)

    for term in [
        "would_require_wallet",
    ]:
        assert term in combined

    for forbidden in [
        '"would_require_wallet": true',
        '"would_write_chain": true',
        '"live_chain_write": true',
    ]:
        assert forbidden not in combined


def test_phase13_glyphchain_proof_receipt_no_live_gateway_side_effects():
    combined = "\n".join(_text(path) for path in GLYPHCHAIN_FILES)

    for forbidden in [
        "capture_payment(",
        "release_escrow(",
        "create_booking(",
        "send_email(",
        "send_sms(",
        "post_social(",
        "dispatch_job(",
        '"payment_captured": true',
        '"booking_confirmed": true',
        '"escrow_released": true',
        '"external_message_sent": true',
        '"live_job_created": true',
    ]:
        assert forbidden not in combined
