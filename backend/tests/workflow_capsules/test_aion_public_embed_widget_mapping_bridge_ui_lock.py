from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text():
    return APP.read_text()


def test_public_embed_widget_mapping_bridge_renderer_exists():
    text = _text()
    assert "renderAionPublicEmbedWidgetMappingBridgeV0" in text
    assert "buildPublicWidgetMappingPreviewV0" in text
    assert "public-embed-widget-mapping-bridge-v0" in text


def test_public_embed_widget_mapping_bridge_renders_required_sections():
    text = _text()
    for term in [
        "AION Embed Widget Mapping Bridge",
        "NormalizedInboundIntent preview",
        "MachineCartRequest preview",
        "Safety boundary",
        "website_form_widget",
        "website_button_widget",
        "embedded_chat_widget",
    ]:
        assert term in text


def test_public_embed_widget_mapping_bridge_is_preview_only():
    text = _text()
    for term in [
        "preview_only",
        "human_review_required",
        "would_create_booking: false",
        "would_create_live_job: false",
        "would_execute_goal_engine: false",
        "would_move_money: false",
        "would_create_payment: false",
        "would_create_escrow: false",
        "would_send_external_messages: false",
        "unauthenticated_public_write_route_exposed: false",
    ]:
        assert term in text


def test_public_embed_widget_mapping_bridge_has_no_live_action_button():
    text = _text()
    blocked = [
        "Execute Now",
        "Run Live",
        "Create Booking",
        "Take Payment",
        "Create Escrow",
        "Send Message",
        "Release Funds",
        "Create Live Job",
    ]
    section = text.split("/* AION LOCK: Public Embed Widget Mapping Bridge v0 */", 1)[1]
    for term in blocked:
        assert term not in section


def test_public_embed_widget_mapping_bridge_exports_window_function():
    text = _text()
    assert "window.renderAionPublicEmbedWidgetMappingBridgeV0" in text
    assert "window.buildPublicWidgetMappingPreviewV0" in text
