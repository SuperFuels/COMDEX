from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
TEXT = TEXT


def test_phase22u_command_bar_helpers_exist():
    for marker in [
        "function getAionPilotCommandBarContext",
        "function activateAionPilotRevisionCommandContext",
        "function getAionPilotCommandBarPlaceholder",
        "function getAionPilotCommandBarValue",
        "function getAionPilotCommandButtonLabel",
        "function applyAionPilotCommandBarRevisionIfActive",
    ]:
        assert marker in TEXT


def test_phase22u_command_revision_router_consumes_mission_thread_commands():
    assert 'commandMode === "approval_draft_revision" || commandMode === "mission_thread"' in TEXT
    assert "applyAionPilotSimpleMissionThreadRevision" in TEXT
    assert "Edited current working draft in place" in TEXT
    assert "return true" in TEXT


def test_phase22u_thread_revision_does_not_overwrite_last_request_or_replan():
    create_index = TEXT.index("if (applyAionPilotCommandBarRevisionIfActive(requestText))")
    last_request_index = TEXT.index("pilotState.last_request = requestText;")
    assert create_index < last_request_index


def test_phase22u_simple_remove_instruction_supports_list_edits():
    assert "normaliseLineForEditMatch" in TEXT
    assert "Removed:" in TEXT
    assert "revised_text" in TEXT
    assert "change_log" in TEXT


def test_phase22u_revision_output_contains_change_log_and_boundary():
    assert "Tracked changes" in TEXT
    assert "Edited in place" in TEXT
    assert "aion-pilot-tracked-change-strip" in TEXT


def test_phase22u_command_placeholder_is_current_thread_specific():
    assert "Tell Pilot what to change in this current mission thread" in TEXT
