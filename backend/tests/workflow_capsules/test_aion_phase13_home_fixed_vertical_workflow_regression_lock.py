from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

HOME_FIXED_FILES = [
    "backend/tests/workflow_capsules/test_aion_home_fixed_vertical_testbed_lock.py",
    "backend/tests/workflow_capsules/test_aion_home_fixed_vertical_testbed_lock_doc.py",
    "docs/rfc/aion_home_fixed_vertical_testbed_lock.tex",
    "backend/modules/aion_gateway/public_intent_gateway.py",
    "backend/modules/aion_gateway/public_widget_request_mapping.py",
    "backend/modules/aion_gateway/public_embed_guard_envelope.py",
]


def _text(path: str) -> str:
    return (ROOT / path).read_text().lower()


def test_phase13_home_fixed_vertical_files_exist():
    for path in HOME_FIXED_FILES:
        assert (ROOT / path).exists(), path


def test_phase13_home_fixed_vertical_identity_is_locked():
    combined = "\n".join(_text(path) for path in HOME_FIXED_FILES)

    for term in [
        "home_fixed",
        "home fixed",
        "home_repair",
    ]:
        assert term in combined


def test_phase13_home_fixed_public_flow_remains_preview_only():
    combined = "\n".join(_text(path) for path in HOME_FIXED_FILES)

    for term in [
        "preview",
        "human_review_required",
        "would_create_payment",
        "would_create_booking",
        "would_create_escrow",
        "would_send_external_message",
    ]:
        assert term in combined

    for forbidden in [
        '"would_create_payment": true',
        '"would_create_booking": true',
        '"would_create_escrow": true',
        '"would_send_external_message": true',
        "auto_confirm_booking",
        "auto_dispatch_job",
        "capture_payment(",
        "release_escrow(",
        "send_email(",
        "send_sms(",
        "post_social(",
    ]:
        assert forbidden not in combined


def test_phase13_home_fixed_vertical_uses_real_service_language():
    combined = "\n".join(_text(path) for path in HOME_FIXED_FILES)

    for term in [
        "repair",
        "quote",
        "customer",
        "job",
    ]:
        assert term in combined


def test_phase13_home_fixed_vertical_does_not_revert_to_costa_testbed():
    combined = "\n".join(_text(path) for path in HOME_FIXED_FILES)

    assert "home_fixed" in combined
    assert "home repair" in combined or "home_repair" in combined
    assert "costa_connect" not in combined
    assert "costa_conexion" not in combined


def test_phase13_home_fixed_vertical_is_safe_for_public_embed():
    combined = "\n".join(
        _text(path)
        for path in [
            "backend/modules/aion_gateway/public_intent_gateway.py",
            "backend/modules/aion_gateway/public_embed_guard_envelope.py",
            "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
        ]
    )

    for term in [
        "preview_only",
        "human_review_required",
        "blocked_reasons",
    ]:
        assert term in combined

    for forbidden in [
        '"live_job_created": true',
        '"booking_confirmed": true',
        '"payment_captured": true',
        '"escrow_released": true',
        '"external_message_sent": true',
    ]:
        assert forbidden not in combined


def test_phase13_home_fixed_vertical_regression_lock_has_no_live_provider_imports():
    combined = "\n".join(_text(path) for path in HOME_FIXED_FILES)

    for forbidden in [
        "smtplib",
        "twilio",
        "sendgrid",
        "mailgun",
        "stripe.checkout",
        "paypalrestsdk",
        "revolut.checkout",
        "google.calendar",
        "calendly",
        "booking_provider",
    ]:
        assert forbidden not in combined
