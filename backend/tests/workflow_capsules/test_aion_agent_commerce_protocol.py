from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.a2a_commerce_service import A2ACommerceService


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _register(service: A2ACommerceService, agent_id: str = "customer-agent"):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    challenge = service.issue_challenge(
        agent_id=agent_id,
        agent_name="Customer Agent",
        public_key_base64=base64.b64encode(public).decode("ascii"),
    )
    signature = private.sign(_canonical(challenge["signature_payload"]))
    verified = service.verify_challenge(
        challenge_id=challenge["challenge_id"],
        signature_base64=base64.b64encode(signature).decode("ascii"),
    )
    assert verified["status"] == "VERIFIED"
    return private


def _signed_request(service, private, body, *, nonce="request-1", path="/api/a2a/v1/tasks"):
    raw = _canonical(body)
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = f"POST\n{path}\n{timestamp}\n{nonce}\n{hashlib.sha256(raw).hexdigest()}".encode()
    return service.authenticate(
        agent_id="customer-agent",
        timestamp=timestamp,
        nonce=nonce,
        signature_base64=base64.b64encode(private.sign(payload)).decode("ascii"),
        method="POST",
        path=path,
        body=raw,
    )


def test_agent_card_registration_signed_task_and_replay_protection(tmp_path):
    service = A2ACommerceService(tmp_path, public_base_url="https://agents.example")
    service.configure_business("builder", {
        "business_name": "Example Builder",
        "description": "Roofing and plumbing",
        "facilitation_fee_bps": 1200,
        "services": [{"service_id": "plumbing", "name": "Emergency plumbing", "pricing_mode": "hourly"}],
    })
    card = service.agent_card("builder")
    assert card["protocolVersion"] == "1.0.0"
    assert card["skills"][0]["id"] == "plumbing"
    assert card["tessaris"]["payments_enabled"] is False

    private = _register(service)
    assert _signed_request(service, private, {"business_id": "builder"})["agent_id"] == "customer-agent"
    with pytest.raises(PermissionError, match="replayed"):
        _signed_request(service, private, {"business_id": "builder"})
    replacement = Ed25519PrivateKey.generate().public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    with pytest.raises(ValueError, match="already_registered"):
        service.issue_challenge(agent_id="customer-agent", agent_name="Imposter", public_key_base64=base64.b64encode(replacement).decode("ascii"))


def test_idempotent_commercial_negotiation_discloses_fee_and_requires_exact_approval(tmp_path):
    service = A2ACommerceService(tmp_path)
    service.configure_business("builder", {
        "business_name": "Example Builder",
        "facilitation_fee_bps": 1200,
        "services": [{"service_id": "plumbing", "name": "Plumber", "pricing_mode": "hourly"}],
    })
    _register(service)
    request = {
        "business_id": "builder",
        "message": "I need a plumber today",
        "intent": {"service_id": "plumbing", "location": "Essex", "budget_minor": 25000},
        "authority": {"can_negotiate": True, "max_purchase_minor": 25000, "full_purchase": True},
    }
    created = service.create_task(agent_id="customer-agent", payload=request, idempotency_key="customer-request-001")
    repeated = service.create_task(agent_id="customer-agent", payload=request, idempotency_key="customer-request-001")
    assert repeated["id"] == created["id"]
    assert created["authority"]["full_purchase"] is False

    offered = service.create_offer(created["id"], business_id="builder", actor_id="owner", payload={
        "service_price_minor": 9500,
        "tax_minor": 0,
        "currency": "GBP",
        "scope": "First-hour callout",
        "terms": "Callout included",
        "availability": "32 minutes",
    })
    offer = offered["offers"][0]
    assert offer["facilitation_fee_minor"] == 1140
    assert offer["total_minor"] == 10640
    assert offered["safety"] == {"payment_created": False, "booking_created": False, "external_message_sent": False}

    with pytest.raises(PermissionError, match="exact_human"):
        service.approve(created["id"], agent_id="customer-agent", offer_hash=offer["offer_hash"], human_confirmed=True, confirmation="APPROVE")
    accepted = service.approve(created["id"], agent_id="customer-agent", offer_hash=offer["offer_hash"], human_confirmed=True,
                               confirmation=f"APPROVE {offer['offer_hash']}")
    assert accepted["status"]["state"] == "completed"
    assert accepted["acceptance"]["payment_created"] is False
    assert accepted["acceptance"]["booking_created"] is False


def test_business_inbox_is_isolated_and_default_channel_is_safe(tmp_path):
    service = A2ACommerceService(tmp_path)
    status = service.status("home-fixed", "Home Fixed")
    assert status["channel"]["state"] == "ACTIVE_LOCAL"
    assert status["channel"]["public_relay_configured"] is False
    assert status["business"]["services"] == []
    assert status["guardrails"]["human_approval_default"] is True

    service.configure_business("other", {"business_name": "Other", "services": []})
    _register(service)
    task = service.create_task(agent_id="customer-agent", payload={"business_id": "home-fixed", "message": "Hello"}, idempotency_key="request-home-1")
    assert [item["id"] for item in service.inbox("home-fixed")] == [task["id"]]
    assert service.inbox("other") == []
    with pytest.raises(PermissionError, match="business_mismatch"):
        service.get_task(task["id"], business_id="other")


def test_rate_limit_is_durable(tmp_path):
    service = A2ACommerceService(tmp_path)
    service.check_rate_limit(bucket="challenge", subject="127.0.0.1", limit=2, window_seconds=60)
    A2ACommerceService(tmp_path).check_rate_limit(bucket="challenge", subject="127.0.0.1", limit=2, window_seconds=60)
    with pytest.raises(PermissionError, match="rate_limit"):
        service.check_rate_limit(bucket="challenge", subject="127.0.0.1", limit=2, window_seconds=60)


def test_market_search_fans_out_and_labels_missing_evidence(tmp_path):
    service = A2ACommerceService(tmp_path)
    for business_id, name, price in (("plumber-a", "Alpha Plumbing", 9500), ("plumber-b", "Bravo Plumbing", 11000)):
        service.configure_business(business_id, {
            "business_name": name,
            "facilitation_fee_bps": 1200,
            "services": [{"service_id": "emergency-plumbing", "name": "Emergency plumber", "description": "Leaks and urgent repairs",
                          "locations": ["Essex"], "pricing_mode": "hourly", "base_price_minor": price,
                          "availability": "Today; confirmation required", "terms_summary": "Insured callout"}],
        })
    _register(service)
    found = service.search_market(agent_id="customer-agent", idempotency_key="market-search-001", payload={
        "service": "emergency plumber", "outcome": "Repair a leaking pipe", "location": "Essex",
        "requested_window": "today", "budget_minor": 25000, "currency": "GBP",
    })
    assert found["candidate_count"] == 2
    assert found["candidates"][0]["business_name"] == "Alpha Plumbing"
    assert found["candidates"][0]["price"]["evidence"] == "INDICATIVE_CATALOGUE"
    assert found["candidates"][0]["reviews"] == {"state": "NOT_AVAILABLE", "rating": None, "review_count": 0}
    assert found["candidates"][0]["completed_jobs"] == {"state": "NOT_VERIFIED", "count": None}
    assert found["pricing_policy"]["undisclosed_surge_pricing_allowed"] is False

    first = found["candidates"][0]
    service.create_offer(first["task_id"], business_id=first["business_id"], actor_id="owner", payload={
        "service_price_minor": 9000, "currency": "GBP", "availability": "Today 15:30", "terms": "Insured; first hour",
    })
    refreshed = service.get_market(found["market_id"], agent_id="customer-agent")
    assert refreshed["candidates"][0]["price"]["evidence"] == "LIVE_OFFER"
    assert refreshed["candidates"][0]["price"]["amount_minor"] == 10080
    assert refreshed["candidates"][0]["next_action"] == "ACCEPT_EXACT_OFFER"


def test_service_intake_gathers_missing_details_and_keeps_images_private(tmp_path):
    service = A2ACommerceService(tmp_path)
    _register(service)
    session = service.start_intake(
        agent_id="customer-agent",
        text="I need a plumber because the kitchen tap is leaking",
        idempotency_key="intake-request-001",
    )
    assert session["ticket"]["service"] == "plumber"
    assert session["awaiting"] == "location"
    assert session["ready_for_market"] is False

    session = service.continue_intake(session["session_id"], agent_id="customer-agent", text="Kensington")
    assert session["ticket"]["location"] == "Kensington"
    assert session["awaiting"] == "requested_window"
    session = service.continue_intake(session["session_id"], agent_id="customer-agent", text="Tomorrow afternoon")
    assert session["awaiting"] == "images"

    session = service.add_intake_attachment(
        session["session_id"], agent_id="customer-agent", filename="leaking-tap.png",
        media_type="image/png", data_base64=base64.b64encode(b"private-image-bytes").decode("ascii"),
    )
    assert session["ticket"]["image_count"] == 1
    assert session["awaiting"] == "contact"
    receipt = session["attachments"][0]
    assert receipt["sha256"] == hashlib.sha256(b"private-image-bytes").hexdigest()
    assert "data_base64" not in receipt

    session = service.continue_intake(
        session["session_id"], agent_id="customer-agent", text="kevin@example.com"
    )
    assert session["ready_for_market"] is True
    assert session["ticket"]["contact"] == {"email": "kevin@example.com"}
    assert session["ticket"]["missing"] == []


def test_service_intake_is_idempotent_and_agent_isolated(tmp_path):
    service = A2ACommerceService(tmp_path)
    _register(service)
    first = service.start_intake(
        agent_id="customer-agent", text="I need an electrician", idempotency_key="intake-idempotent-1"
    )
    repeated = service.start_intake(
        agent_id="customer-agent", text="This must not replace the original", idempotency_key="intake-idempotent-1"
    )
    assert repeated["session_id"] == first["session_id"]
    with pytest.raises(PermissionError, match="agent_mismatch"):
        service.continue_intake(first["session_id"], agent_id="another-agent", text="London")


def test_market_voice_input_streams_partial_words_then_checks_the_full_recording():
    page = (
        Path(__file__).resolve().parents[2]
        / "modules"
        / "aion_business"
        / "static"
        / "tessaris-market.html"
    ).read_text(encoding="utf-8")
    assert "voiceRecognition.interimResults=true" in page
    assert "writing your words live" in page
    assert "transcribeVoiceRecording(blob)" in page
    assert "final wording checked by Local Whisper" in page


def test_public_market_page_runs_an_explicitly_fictional_demo():
    page = (
        Path(__file__).resolve().parents[2]
        / "modules"
        / "aion_business"
        / "static"
        / "tessaris-market.html"
    ).read_text(encoding="utf-8")
    assert '<body class="demo-mode">' in page
    assert "Illustrative demo" in page
    assert "No real request, booking or purchase" in page
    assert "startDemo();" in page
    assert "3 fictional example bids" in page
    assert "Accept demo bid" in page
