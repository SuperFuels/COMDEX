import json

from backend.services.aion_mission_mode.website_foundation_extractor import (
    collect_website_evidence_from_html,
    normalise_url,
)


GENERIC_SITE = """
<html>
<head>
  <title>Blue Lemon Cafe | Brunch and Coffee</title>
  <link rel="icon" href="/favicon.png">
  <meta property="og:image" content="/social-cover.jpg">
  <style>
    :root { --brand-primary: #0F766E; }
    body { color: #102A43; font-family: "Avenir Next", Arial, sans-serif; }
  </style>
</head>
<body>
<img src="/blue-lemon-logo.svg" alt="Blue Lemon Cafe logo">
<h1>Blue Lemon Cafe</h1>
<h2>Menu</h2>
<p>Breakfast plates, sandwiches, vegan cakes, fresh juices and speciality coffee.</p>
<h2>Private Catering</h2>
<p>We offer catering packages for offices, birthdays and local events.</p>
<h2>Contact</h2>
<p>Email hello@bluelemon.test Call +44 7700 900123</p>
<p>Opening hours Monday to Saturday 8am to 4pm.</p>
<p>Book a table or order catering online.</p>
<a href="https://instagram.com/bluelemoncafe">Instagram</a>
</body>
</html>
"""


def test_phase24b_normalise_url_adds_https():
    assert normalise_url("example.com") == "https://example.com"


def test_phase24b_evidence_collector_extracts_public_website_evidence():
    evidence = collect_website_evidence_from_html("https://bluelemon.test", GENERIC_SITE)

    assert evidence["url"] == "https://bluelemon.test"
    assert evidence["domain"] == "bluelemon.test"
    assert "Blue Lemon Cafe" in evidence["title"]
    assert "Menu" in evidence["headings"]
    assert "Private Catering" in evidence["headings"]
    assert "Breakfast plates" in evidence["visible_text"]
    assert "hello@bluelemon.test" in evidence["emails"]
    assert "+44 7700 900123" in evidence["phones"]
    assert "https://instagram.com/bluelemoncafe" in evidence["social_links"]
    assert "https://bluelemon.test/blue-lemon-logo.svg" in evidence["logo_candidates"]
    assert "https://bluelemon.test/favicon.png" in evidence["icon_candidates"]
    assert "https://bluelemon.test/social-cover.jpg" in evidence["social_image_candidates"]
    assert "#0F766E" in evidence["colour_candidates"]
    assert any("Avenir Next" in item for item in evidence["font_candidates"])
    assert {"name": "--brand-primary", "value": "#0F766E"} in evidence["css_custom_properties"]
    assert evidence["font_roles"]["body"] == "Avenir Next"
    assert evidence["live_external_side_effect"] is False


def test_phase24b_evidence_payload_is_json_serialisable_for_openai():
    evidence = collect_website_evidence_from_html("https://bluelemon.test", GENERIC_SITE)
    encoded = json.dumps(evidence, sort_keys=True)

    assert "Blue Lemon Cafe" in encoded
    assert "speciality coffee" in encoded
    assert "live_external_side_effect" in encoded


def test_phase24b_external_css_can_supply_visual_tokens():
    evidence = collect_website_evidence_from_html(
        "https://bluelemon.test",
        "<html><head><link rel='stylesheet' href='/styles.css'></head><body>Blue Lemon</body></html>",
        supplemental_css=':root{--brand:#14A7DF} h1{font-family:"Bebas Neue", sans-serif}',
    )

    assert "#14A7DF" in evidence["colour_candidates"]
    assert evidence["font_candidates"] == ["Bebas Neue"]
    assert evidence["font_roles"]["heading"] == "Bebas Neue"
    assert {"name": "--brand", "value": "#14A7DF"} in evidence["css_custom_properties"]
