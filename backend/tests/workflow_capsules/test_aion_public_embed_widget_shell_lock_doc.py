from pathlib import Path

DOC = Path("docs/rfc/aion_public_embed_widget_shell_lock.tex")


def _text():
    return DOC.read_text()


def test_public_embed_widget_shell_doc_exists():
    assert DOC.exists()


def test_public_embed_widget_shell_doc_lists_status_and_purpose():
    text = _text()
    assert "Phase 12B --- Public Website Embed Widget Shell v0" in text
    assert "frontend-visible public website embed widget shell" in text
    assert "Phase 12A" in text
    assert "Public Website Intent Gateway" in text


def test_public_embed_widget_shell_doc_lists_renderer():
    text = _text()
    assert "desktop/mac/src/app.js" in text
    assert "renderAionPublicEmbedWidgetShellV0" in text
    assert "window.renderAionPublicEmbedWidgetShellV0" in text
    assert "data-aion-lock=\"public-embed-widget-shell-v0\"" in text


def test_public_embed_widget_shell_doc_lists_preview_surfaces():
    text = _text()
    for term in [
        "embed\\_script\\_preview",
        "website\\_form\\_widget\\_preview",
        "website\\_button\\_widget\\_preview",
        "embedded\\_chat\\_widget\\_preview",
    ]:
        assert term in text


def test_public_embed_widget_shell_doc_lists_gateway_mapping():
    text = _text()
    assert "NormalizedInboundIntent" in text
    assert "MachineCartRequest" in text
    assert "public_intent_gateway" in text


def test_public_embed_widget_shell_doc_lists_required_guards():
    text = _text()
    for term in [
        "tenant/business key validation",
        "signed request validation",
        "rate limiting",
        "abuse protection",
        "human review",
    ]:
        assert term in text


def test_public_embed_widget_shell_doc_states_safety():
    text = _text()
    for term in [
        "create a booking",
        "create a live job",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "release funds",
        "send external messages",
        "expose an unauthenticated public write route",
        "preview_only = true",
    ]:
        assert term in text


def test_public_embed_widget_shell_doc_requires_frontend_smoke_test():
    text = _text()
    assert "Frontend Smoke Test Required" in text
    assert "window.renderAionPublicEmbedWidgetShellV0" in text
    assert "no live action button is visible" in text


def test_public_embed_widget_shell_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
