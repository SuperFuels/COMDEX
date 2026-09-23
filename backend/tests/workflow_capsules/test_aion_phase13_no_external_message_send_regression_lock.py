from pathlib import Path


GATEWAY_MODULES = [
    "backend/modules/aion_gateway/public_intent_gateway.py",
    "backend/modules/aion_gateway/public_widget_request_mapping.py",
    "backend/modules/aion_gateway/public_embed_guard_envelope.py",
    "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
    "backend/modules/aion_gateway/agent_channels.py",
    "backend/modules/aion_gateway/a2a_job_trace.py",
    "backend/modules/aion_gateway/a2a_job_evidence_settlement.py",
    "backend/modules/aion_gateway/a2a_handshake_preview.py",
    "backend/modules/aion_gateway/fulfilment_job.py",
    "backend/modules/aion_gateway/fulfilment_job_core.py",
    "backend/modules/aion_gateway/machine_cart.py",
    "backend/modules/aion_gateway/parallel_catalog.py",
    "backend/modules/aion_gateway/parallel_discovery.py",
    "backend/modules/aion_gateway/exceptions.py",
]


FORBIDDEN_LIVE_MESSAGE_SEND_TERMS = [
    ".send_email(",
    "send_email(",
    ".send_message(",
    "send_message(",
    ".send_whatsapp(",
    "send_whatsapp(",
    ".send_sms(",
    "send_sms(",
    ".send_mail(",
    "send_mail(",
    "smtp.sendmail",
    "smtplib",
    "twilio",
    "whatsapp_business",
    "whatsapp_business_api",
    "messagebird",
    "sendgrid",
    "mailgun",
    "postmark",
    "resend.emails.send",
    "external_message_provider",
    "live_message_send",
]


ALLOWED_PREVIEW_TERMS = [
    "would_send_external_messages",
    "would_send_external_message",
    "no_external_message_send",
    "send external messages",
    "do not send email",
    "do not send WhatsApp",
]


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_phase13_no_external_message_modules_exist():
    for path in GATEWAY_MODULES:
        assert Path(path).exists(), path


def test_phase13_no_external_message_modules_do_not_import_live_message_providers():
    for path in GATEWAY_MODULES:
        text = _text(path).lower()

        for forbidden in FORBIDDEN_LIVE_MESSAGE_SEND_TERMS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_phase13_no_external_message_preview_flags_remain_false():
    combined = "\n".join(_text(path) for path in GATEWAY_MODULES)

    assert "would_send_external_messages" in combined or "would_send_external_message" in combined
    assert "False" in combined or "false" in combined
    assert "preview_only" in combined


def test_phase13_agent_channels_explicitly_blocks_external_sends():
    text = _text("backend/modules/aion_gateway/agent_channels.py").lower()

    # Agent channels are preview/routing contracts only. They may describe
    # channels, but must not import or execute live external message providers.
    for forbidden in [
        "smtplib",
        "twilio",
        "sendgrid",
        "mailgun",
        "postmark",
        "messagebird",
        "whatsapp_business_api",
        "resend.emails.send",
        "live_message_send",
        "external_message_provider",
    ]:
        assert forbidden not in text

    for term in [
        "preview",
        "routing_status",
        "blocked",
    ]:
        assert term in text


def test_phase13_public_intent_gateway_blocks_external_message_send():
    text = _text("backend/modules/aion_gateway/public_intent_gateway.py")

    assert "would_send_external_message" in text or "would_send_external_messages" in text
    assert "False" in text or "false" in text


def test_phase13_public_embed_guard_envelope_blocks_external_message_send():
    text = _text("backend/modules/aion_gateway/public_embed_guard_envelope.py")

    assert "would_send_external_messages" in text
    assert '"would_send_external_messages": False' in text


def test_phase13_public_embed_human_review_handoff_blocks_external_message_send():
    text = _text("backend/modules/aion_gateway/public_embed_human_review_handoff.py")

    assert "approval_can_send_external_messages" in text
    assert '"approval_can_send_external_messages": False' in text


def test_phase13_no_external_message_regression_has_no_public_send_route_terms():
    combined = "\n".join(_text(path).lower() for path in GATEWAY_MODULES)

    for forbidden in [
        "/send-email",
        "/send-message",
        "/send-whatsapp",
        "/send-sms",
        "post_external_message",
        "execute_external_send",
    ]:
        assert forbidden not in combined


def test_phase13_no_external_message_is_preview_only_until_guarded_approval():
    combined = "\n".join(_text(path).lower() for path in GATEWAY_MODULES)

    assert "human_review" in combined
    assert "preview_only" in combined
    assert "external" in combined
