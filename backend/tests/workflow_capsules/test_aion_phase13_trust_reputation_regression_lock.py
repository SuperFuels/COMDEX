from pathlib import Path


TRUST_FILES = [
    "backend/modules/aion_gateway/trust_reputation.py",
    "backend/modules/aion_gateway/a2a_trust_summary.py",
    "backend/modules/aion_gateway/a2a_trust_summary.py",
    "backend/modules/aion_gateway/public_embed_guard_envelope.py",
    "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
]

DOC = Path("docs/rfc/aion_phase13_trust_reputation_regression_lock.tex")


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_phase13_trust_reputation_modules_exist():
    for path in TRUST_FILES:
        assert Path(path).exists(), path


def test_phase13_trust_reputation_doc_exists():
    assert DOC.exists()


def test_phase13_trust_reputation_no_runtime_random_identity():
    for path in TRUST_FILES:
        text = _text(path).lower()
        for forbidden in [
            "uuid.uuid4",
            "random.uuid",
            "secrets.token",
            "random_id",
            "runtime_random",
        ]:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_phase13_trust_reputation_no_live_payment_or_booking_side_effects():
    for path in TRUST_FILES:
        text = _text(path).lower()

        # Preview flags such as would_create_payment=False are allowed.
        # Live provider/action couplings remain forbidden.
        for forbidden in [
            "capture_payment",
            "release_payment",
            "release_escrow",
            "transfer_funds",
            "create_booking(",
            "book_job(",
            "dispatch_job(",
            "smtp",
            "twilio",
            "sendgrid",
            "live_payment_provider",
            "live_booking_provider",
            "external_message_provider",
        ]:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_phase13_trust_reputation_summary_is_preview_or_read_model_only():
    text = _text("backend/modules/aion_gateway/trust_reputation.py").lower()

    for term in [
        "trust",
        "reputation",
        "summary",
    ]:
        assert term in text

    for forbidden in [
        "mutate_payment",
        "move_money",
        "booking_confirmed",
        "external_message_sent",
        "auto_approve_by_reputation",
    ]:
        assert forbidden not in text


def test_phase13_a2a_trust_summary_endpoint_is_read_only():
    text = _text("backend/modules/aion_gateway/a2a_trust_summary.py").lower()

    for term in [
        "trust",
        "summary",
        "human_review_required",
    ]:
        assert term in text

    # Preview flags are allowed; live actions/providers are not.
    for forbidden in [
        "post_social(",
        "send_email(",
        "send_sms(",
        "capture_payment",
        "release_escrow",
        "create_booking(",
        '"live_status_polling_enabled": true',
    ]:
        assert forbidden not in text


def test_phase13_public_guard_surfaces_trust_without_side_effects():
    combined = "\n".join(
        _text(path).lower()
        for path in [
            "backend/modules/aion_gateway/public_embed_guard_envelope.py",
            "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
        ]
    )

    for term in [
        "human",
        "review",
        "preview",
    ]:
        assert term in combined

    for forbidden in [
        "trust_can_autobook",
        "trust_can_move_money",
        "trust_can_send_message",
        "auto_approve_by_reputation",
    ]:
        assert forbidden not in combined


def test_phase13_trust_reputation_doc_is_locked():
    text = DOC.read_text(encoding="utf-8")
    assert "Phase 13H --- Trust/Reputation Regression v0" in text
    assert "Status: LOCKED" in text
    assert "AION-PHASE13H-TRUST-REPUTATION-REGRESSION-V0" in text
