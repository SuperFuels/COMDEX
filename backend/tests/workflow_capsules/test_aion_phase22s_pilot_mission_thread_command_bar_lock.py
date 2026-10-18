from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22s_command_bar_helpers_exist():
    for marker in [
        "function getAionPilotCommandBarContext",
        "function activateAionPilotRevisionCommandContext",
        "function getAionPilotCommandBarPlaceholder",
        "function getAionPilotCommandBarValue",
        "function getAionPilotCommandButtonLabel",
        "function applyAionPilotCommandBarRevisionIfActive",
    ]:
        assert marker in TEXT


def test_phase22s_command_bar_no_longer_reuses_original_request_in_thread_mode():
    assert "getAionPilotCommandBarValue(pilotState)" in TEXT
    assert "getAionPilotCommandBarPlaceholder(pilotState)" in TEXT
    assert "getAionPilotCommandButtonLabel(pilotState, hasDraft)" in TEXT
    assert '${escapeHtml(pilotState.last_request || "")}</textarea>' not in TEXT


def test_phase22s_revise_button_activates_current_context_not_new_mission():
    assert "__aionPilotRevisionCommandBarClickHandlerInstalled" in TEXT
    assert "[data-aion-pilot-feedback-revise]" in TEXT
    assert "event.stopImmediatePropagation()" in TEXT
    assert "activateAionPilotRevisionCommandContext()" in TEXT


def test_phase22s_submit_routes_revision_before_last_request_overwrite():
    submit_index = TEXT.index("applyAionPilotCommandBarRevisionIfActive(requestText)")
    last_request_index = TEXT.index("pilotState.last_request = requestText;")
    assert submit_index < last_request_index


def test_phase22s_revision_output_is_specific_to_current_approval_item():
    assert "buildAionPilotRevisionDraftOutput" in TEXT
    assert "Revised current approval draft" in TEXT
    assert "It has not started a new mission" in TEXT
    assert "Approval boundary" in TEXT
