from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _text():
    return APP_JS.read_text()


def test_public_embed_widget_shell_renderer_exists():
    text = _text()
    assert "AION LOCK: Public Website Embed Widget Shell v0" in text
    assert "renderAionPublicEmbedWidgetShellV0" in text
    assert "window.renderAionPublicEmbedWidgetShellV0" in text
    assert "window.__aionPublicEmbedWidgetShellV0Installed" in text


def test_public_embed_widget_shell_lock_marker_exists():
    text = _text()
    assert 'data-aion-lock="public-embed-widget-shell-v0"' in text
    assert "AION Embed Widget Shell" in text
    assert "Public Website Gateway" in text
    assert "Preview only" in text


def test_public_embed_widget_shell_lists_surfaces():
    text = _text()
    for term in [
        "embed_script_preview",
        "website_form_widget_preview",
        "website_button_widget_preview",
        "embedded_chat_widget_preview",
    ]:
        assert term in text


def test_public_embed_widget_shell_maps_to_gateway_contracts():
    text = _text()
    assert "NormalizedInboundIntent" in text
    assert "MachineCartRequest" in text
    assert "public_intent_gateway" in text


def test_public_embed_widget_shell_lists_required_guards():
    text = _text()
    for term in [
        "tenant_key_required",
        "signed_request_required",
        "rate_limiting_required",
        "abuse_protection_required",
        "human_review_required",
    ]:
        assert term in text


def test_public_embed_widget_shell_safety_flags_are_non_executing():
    text = _text()
    for term in [
        "would_create_booking: false",
        "would_create_live_job: false",
        "would_execute_goal_engine: false",
        "would_bypass_human_review: false",
        "would_move_money: false",
        "would_move_pho: false",
        "would_require_wallet: false",
        "would_create_payment: false",
        "would_create_escrow: false",
        "would_release_funds: false",
        "would_send_external_messages: false",
        "unauthenticated_public_write_route_exposed: false",
    ]:
        assert term in text


def test_public_embed_widget_shell_does_not_expose_live_action_labels():
    text = _text()
    forbidden = [
        "Book Now Live",
        "Create Live Job",
        "Execute Goal Engine",
        "Take Payment",
        "Create Escrow",
        "Release Funds",
        "Send External Message",
        "Bypass Human Review",
    ]
    for term in forbidden:
        assert term not in text
