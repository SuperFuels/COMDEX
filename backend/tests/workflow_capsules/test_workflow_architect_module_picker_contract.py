from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js not found"
    return APP_JS.read_text(encoding="utf-8")


def test_plus_opens_module_picker_first() -> None:
    text = _read()

    assert "renderAionArchitectModulePicker" in text
    assert "__aionArchitectModulePickerOpen = true" in text
    assert "+ opens module picker first" in text


def test_module_picker_has_make_style_groups() -> None:
    text = _read()

    for label in [
        "Flow Control",
        "Tools",
        "Text Parser",
        "AI",
        "Apps",
        "Approval",
        "Taught Processes",
    ]:
        assert label in text


def test_module_picker_has_flow_control_modules() -> None:
    text = _read()

    for action in [
        "logic.if_else",
        "logic.router",
        "logic.merge",
        "logic.iterator",
        "logic.array_aggregator",
        "logic.repeater",
    ]:
        assert action in text


def test_module_picker_has_tools_and_text_parser_modules() -> None:
    text = _read()

    for action in [
        "tools.set_variable",
        "tools.get_variable",
        "tools.compose_string",
        "text.match_pattern",
        "text.html_to_text",
        "text.replace",
    ]:
        assert action in text


def test_module_picker_has_ai_and_app_modules() -> None:
    text = _read()

    for action in [
        "aion.run_agent",
        "aion.extract_information",
        "aion.summarise_text",
        "gmail.watch_emails",
        "gmail.create_draft",
        "hubspot.create_or_update_contact",
        "mailchimp.add_subscriber",
    ]:
        assert action in text
