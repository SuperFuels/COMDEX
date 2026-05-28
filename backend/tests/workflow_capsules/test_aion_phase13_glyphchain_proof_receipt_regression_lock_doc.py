from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/rfc/aion_phase13_glyphchain_proof_receipt_regression_lock.tex"


def _doc() -> str:
    return DOC.read_text().lower()


def test_phase13_glyphchain_proof_receipt_doc_exists():
    assert DOC.exists()


def test_phase13_glyphchain_proof_receipt_doc_has_lock_identity():
    text = _doc()

    for term in [
        "phase 13j",
        "glyphchain",
        "proof receipt",
        "regression lock",
    ]:
        assert term in text


def test_phase13_glyphchain_proof_receipt_doc_declares_preview_boundary():
    text = _doc()

    for term in [
        "preview-safe",
        "read-only",
        "would\\_write\\_chain",
        "would\\_require\\_wallet",
    ]:
        assert term in text


def test_phase13_glyphchain_proof_receipt_doc_blocks_live_side_effects():
    text = _doc()

    for term in [
        "must not",
        "broadcast",
        "wallet",
        "payment",
        "booking",
        "escrow",
        "external-message",
    ]:
        assert term in text


def test_phase13_glyphchain_proof_receipt_doc_has_validation_commands():
    text = _doc()

    for term in [
        "pytest",
        "run_goal_engine_focused_lock_suite.sh",
        "compileall",
    ]:
        assert term in text


def test_phase13_glyphchain_proof_receipt_doc_has_lock_footer():
    text = _doc()

    for term in [
        "lock id:",
        "aion-phase13j-glyphchain-proof-receipt-regression-v0",
        "maintainer: tessaris ai",
        "author: kevin robinson",
    ]:
        assert term in text
