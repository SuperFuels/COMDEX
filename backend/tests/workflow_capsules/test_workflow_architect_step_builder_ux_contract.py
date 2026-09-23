from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js not found"
    return APP_JS.read_text(encoding="utf-8")


def test_workflow_architect_has_two_build_modes() -> None:
    text = _read()

    assert "__aionWorkflowArchitectBuildMode" in text
    assert 'data-workflow-architect-build-mode="describe"' in text
    assert 'data-workflow-architect-build-mode="steps"' in text
    assert "Describe workflow" in text
    assert "Build step-by-step" in text


def test_step_builder_has_connector_action_catalogue() -> None:
    text = _read()

    assert "getWorkflowArchitectConnectorActionCatalogue" in text
    assert "flattenWorkflowArchitectConnectorActions" in text
    assert "getWorkflowArchitectConnectorAction(actionId)" in text
    assert "gmail.watch_emails" in text
    assert "gmail.search_emails" in text
    assert "gmail.get_email" in text
    assert "gmail.create_draft" in text
    assert "gmail.list_attachments" in text


def test_locked_gmail_actions_are_visible_but_locked() -> None:
    text = _read()

    assert "Locked / future-only" in text
    assert "gmail.send_email" in text
    assert "gmail.reply_email" in text
    assert "gmail.send_draft" in text
    assert "gmail.delete_email" in text
    assert "gmail.api_call" in text
    assert "locked: true" in text


def test_user_steps_include_selected_connector_action_id() -> None:
    text = _read()

    assert "action_id:" in text
    assert "getWorkflowArchitectConnectorAction(step.action_id)" in text
    assert "selectedAction?.requires_approval" in text
    assert "selectedAction?.locked === true" in text


def test_step_builder_action_selection_control_exists() -> None:
    text = _read()

    assert "renderWorkflowArchitectConnectorActionPicker" in text
    assert "data-workflow-architect-select-action" in text
    assert "workflow-architect-action-option" in text
    assert "workflow-architect-step-visual-row" in text
