from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_business_connections_summary_has_route_specific_card_styling():
    scope = 'html body .aion-connections-page [data-aion-connections-business-map="true"]'
    assert scope in APP
    assert "border-top:4px solid var(--connections-blue) !important" in APP
    assert "border-radius:18px !important" in APP
    assert f"{scope} .aion-boardroom-connection-row" in APP
    assert "border-radius:14px !important" in APP
    assert f"{scope} .aion-boardroom-connection-tile" in APP
    assert "min-width:220px !important" in APP


def test_business_connections_status_and_review_use_named_styled_containers():
    assert 'class="aion-connections-map-status"' in APP
    assert 'class="aion-connections-map-review"' in APP
    assert ".aion-connections-page .aion-connections-map-status" in APP
    assert ".aion-connections-page .aion-connections-map-review" in APP


def test_business_connections_layout_remains_responsive():
    assert "grid-template-columns:145px minmax(0,1fr) !important" in APP
    assert "grid-template-columns:1fr !important" in APP

