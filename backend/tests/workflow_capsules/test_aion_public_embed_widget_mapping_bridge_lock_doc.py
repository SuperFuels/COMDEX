from pathlib import Path

DOC = Path("docs/rfc/aion_public_embed_widget_mapping_bridge_lock.tex")


def _text():
    return DOC.read_text()


def test_public_embed_widget_mapping_bridge_doc_exists():
    assert DOC.exists()


def test_public_embed_widget_mapping_bridge_doc_names_phase():
    text = _text()
    assert "Phase 12D" in text
    assert "Public Embed Widget Mapping Bridge v0" in text


def test_public_embed_widget_mapping_bridge_doc_lists_exports():
    text = _text()
    assert "window.buildPublicWidgetMappingPreviewV0" in text
    assert "window.renderAionPublicEmbedWidgetMappingBridgeV0" in text
    assert "public-embed-widget-mapping-bridge-v0" in text


def test_public_embed_widget_mapping_bridge_doc_lists_widget_sources():
    text = _text()
    for term in [
        "website\\_form\\_widget",
        "website\\_button\\_widget",
        "embedded\\_chat\\_widget",
        "unsupported_widget_source",
    ]:
        assert term in text


def test_public_embed_widget_mapping_bridge_doc_lists_preview_sections():
    text = _text()
    for term in [
        "NormalizedInboundIntent",
        "MachineCartRequest",
        "safety boundary",
    ]:
        assert term in text


def test_public_embed_widget_mapping_bridge_doc_states_safety():
    text = _text()
    for term in [
        "preview_only = true",
        "human_review_required = true",
        "would_create_booking = false",
        "would_create_live_job = false",
        "would_execute_goal_engine = false",
        "would_move_money = false",
        "would_create_payment = false",
        "would_create_escrow = false",
        "would_release_funds = false",
        "would_send_external_messages = false",
        "unauthenticated_public_write_route_exposed = false",
    ]:
        assert term in text


def test_public_embed_widget_mapping_bridge_doc_requires_frontend_smoke_test():
    text = _text()
    assert "Frontend Smoke Test Required" in text
    assert "typeof window.renderAionPublicEmbedWidgetMappingBridgeV0" in text
    assert "no live action button is visible" in text


def test_public_embed_widget_mapping_bridge_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
