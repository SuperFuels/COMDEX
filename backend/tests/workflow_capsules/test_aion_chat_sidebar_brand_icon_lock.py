from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_chat_sidebar_uses_a_bounded_outline_svg_in_every_workspace():
    assert 'style.id = "aion-branded-chat-sidebar-icon-v1"' in APP
    assert '[data-tab="aion_chat"] .aion-sidebar-chat-icon' in APP
    assert "width:24px!important" in APP
    assert "max-width:24px!important" in APP
    assert "fill:none!important" in APP
    assert "stroke:currentColor!important" in APP


def test_legacy_generated_badge_is_disabled_for_chat_route():
    assert '[data-tab="aion_chat"] .aion-workflow-nav-icon::before' in APP
    assert "content:none!important" in APP
    assert "display:none!important" in APP


def test_chat_icon_has_branded_hover_and_active_states():
    assert '[data-tab="aion_chat"]:not(.active):not(.app-tab-active):hover' in APP
    assert "background:#eef5ff!important" in APP
    assert '[data-tab="aion_chat"].app-tab-active .aion-sidebar-chat-icon' in APP
    assert "stroke:#fff!important" in APP

