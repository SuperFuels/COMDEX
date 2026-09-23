from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js not found"
    return APP_JS.read_text(encoding="utf-8")


def test_ai_architect_opens_as_canvas_mode_not_modal_first() -> None:
    text = _read()

    assert "__aionWorkflowArchitectCanvasMode" in text
    assert "renderWorkflowArchitectCanvasMode" in text
    assert "data-workflow-architect-canvas-mode" in text
    assert "Back to canvas" in text


def test_ai_architect_canvas_mode_has_simple_user_flow_language() -> None:
    text = _read()

    assert "Use this app" in text
    assert "do this" in text
    assert "then do this" in text
    assert "Build from plain English or clear app-by-app steps" in text


def test_ai_architect_has_gmail_lead_pipeline_preset() -> None:
    text = _read()

    assert "seedWorkflowArchitectLeadPipelinePreset" in text
    assert "data-workflow-architect-preset-lead-pipeline" in text
    assert "gmail.watch_emails" in text
    assert "hubspot.create_or_update_contact" in text
    assert "mailchimp.add_subscriber" in text
    assert "gmail.create_draft" in text
    assert "aion.human_approval" in text


def test_guided_user_steps_preserve_connector_action_id() -> None:
    text = _read()

    assert "action_id:" in text
    assert "action_label:" in text
    assert "user_steps:" in text
    assert "getWorkflowArchitectApprovedUserSteps" in text


def test_canvas_mode_keeps_live_send_and_external_writes_safe() -> None:
    text = _read()

    assert "Live send:</strong> Disabled" in text
    assert "External writes:</strong> Approval gated" in text
    assert "Dry-run only" in text
    assert "Requires valid dry-run + confirmation" in text
