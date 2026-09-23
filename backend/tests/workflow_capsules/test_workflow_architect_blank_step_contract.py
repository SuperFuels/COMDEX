from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js not found"
    return APP_JS.read_text(encoding="utf-8")


def test_ai_architect_starts_with_one_blank_step_contract() -> None:
    text = _read()

    assert "createAionArchitectBlankStep" in text
    assert "ensureAionArchitectHasOneBlankStep" in text
    assert "step starts as one blank step" in text


def test_ai_architect_supports_step_kinds() -> None:
    text = _read()

    for token in [
        "trigger",
        "app_action",
        "ai_action",
        "logic",
        "router",
        "tool",
        "approval",
    ]:
        assert token in text


def test_ai_architect_has_app_dropdown_and_action_picker() -> None:
    text = _read()

    assert "getAionArchitectAppOptions" in text
    assert "getAionArchitectActionOptionsForStep" in text
    assert "Choose app / system" in text
    assert "Choose action" in text


def test_ai_architect_modal_icons_have_handlers() -> None:
    text = _read()

    assert "data-aion-architect-settings-more" in text
    assert "data-aion-architect-settings-expand" in text
    assert "data-aion-architect-settings-help" in text
    assert "data-aion-architect-close-settings" in text
    assert "__aionArchitectSettingsMore" in text
    assert "__aionArchitectSettingsExpanded" in text
    assert "__aionArchitectSettingsHelp" in text


def test_ai_architect_includes_non_app_first_step_actions() -> None:
    text = _read()

    for action_id in [
        "logic.if_else",
        "logic.router",
        "logic.filter",
        "browser.scrape_detail",
        "tools.set_variable",
        "aion.human_approval",
    ]:
        assert action_id in text
