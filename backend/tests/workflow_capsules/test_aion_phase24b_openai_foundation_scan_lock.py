import json

from backend.services.aion_mission_mode.business_foundation_llm_extractor import (
    build_extraction_prompt,
    call_openai_for_foundation,
    extract_json_object,
    normalise_foundation_json,
    scan_html_with_openai_for_tests,
)
from backend.services.aion_mission_mode.website_scan_usage_gate import website_scan_allowed


GENERIC_SITE = """
<html>
<head><title>Example Studio</title></head>
<body>
<h1>Example Studio</h1>
<p>We design websites, brand systems and booking funnels for local businesses.</p>
<p>Call +44 7000 111222 or email hello@example.studio.</p>
<p>Book a free consultation.</p>
</body>
</html>
"""


def test_phase24b_usage_gate_allows_local_dev_by_default(monkeypatch):
    monkeypatch.delenv("AION_REQUIRE_SCAN_LOGIN", raising=False)
    result = website_scan_allowed({})

    assert result["allowed"] is True
    assert result["reason"] == "allowed"
    assert result["user_ref"] == "local_dev"


def test_phase24b_usage_gate_can_require_login(monkeypatch):
    monkeypatch.setenv("AION_REQUIRE_SCAN_LOGIN", "1")
    result = website_scan_allowed({})

    assert result["allowed"] is False
    assert result["reason"] == "login_required_before_openai_scan"


def test_phase24b_prompt_requests_strict_json_and_all_foundation_fields():
    evidence = {
        "url": "https://example.studio",
        "title": "Example Studio",
        "headings": ["Services", "Contact"],
        "visible_text": "Example Studio designs websites. hello@example.studio",
    }

    prompt = build_extraction_prompt(evidence)

    assert "Return ONLY valid JSON" in prompt
    assert "business_name" in prompt
    assert "products_services" in prompt
    assert "source_facts" in prompt
    assert "Example Studio designs websites" in prompt


def test_phase24b_extract_json_object_accepts_raw_json_or_wrapped_text():
    assert extract_json_object('{"business_name":"A"}')["business_name"] == "A"
    assert extract_json_object('Here: {"business_name":"B"} done')["business_name"] == "B"


def test_phase24b_normalise_foundation_json_keeps_schema_fields():
    raw = {
        "business_name": "Example Studio",
        "business_type": "services",
        "products_services": ["Website design", "Brand systems"],
        "target_customers": ["Local businesses"],
        "contact_email": "hello@example.studio",
        "phone_number": "+44 7000 111222",
    }

    result = normalise_foundation_json(raw, "example.studio")

    assert result["business_name"] == "Example Studio"
    assert result["business_type"] == "services"
    assert result["website"] == "https://example.studio"
    assert result["products_services"] == "Website design\nBrand systems"
    assert result["target_customers"] == "Local businesses"
    assert result["contact_email"] == "hello@example.studio"
    assert result["phone_number"] == "+44 7000 111222"


def test_phase24b_openai_call_uses_transport_and_returns_json(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_transport(payload):
        encoded = json.dumps(payload)
        assert payload["model"]
        assert payload["temperature"] == 0.1
        assert "Example Studio" in encoded
        return {
            "output_text": json.dumps({
                "business_name": "Example Studio",
                "business_type": "services",
            })
        }

    result = call_openai_for_foundation(
        {"url": "https://example.studio", "visible_text": "Example Studio"},
        transport=fake_transport,
    )

    assert result["business_name"] == "Example Studio"


def test_phase24b_scan_html_with_openai_for_tests_uses_evidence_not_hardcoding():
    def fake_transport(payload):
        encoded = json.dumps(payload)
        assert "Example Studio" in encoded
        assert "hello@example.studio" in encoded
        return {
            "output_text": json.dumps({
                "business_name": "Example Studio",
                "industry": "Website design and brand systems",
                "business_type": "services",
                "products_services": ["Website design", "Brand systems", "Booking funnels"],
                "contact_email": "hello@example.studio",
                "phone_number": "+44 7000 111222",
                "calls_to_action": ["Book a free consultation"],
                "source_facts": ["We design websites, brand systems and booking funnels for local businesses."],
            })
        }

    result = scan_html_with_openai_for_tests(
        "https://example.studio",
        GENERIC_SITE,
        transport=fake_transport,
    )

    fields = result["extracted_fields"]

    assert result["ok"] is True
    assert result["provider"] == "openai"
    assert fields["business_name"] == "Example Studio"
    assert fields["products_services"] == "Website design\nBrand systems\nBooking funnels"
    assert fields["contact_email"] == "hello@example.studio"
    assert result["live_external_side_effect"] is False
