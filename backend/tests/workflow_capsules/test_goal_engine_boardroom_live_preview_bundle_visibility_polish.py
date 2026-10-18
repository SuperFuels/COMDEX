from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text() -> str:
    return APP.read_text()


def test_decomposition_panel_reads_top_level_and_machine_trace_preview_fields():
    text = _text()

    assert "const machineTrace = source.machine_trace || source.trace || {};" in text
    assert "source.goal_decomposition_previews" in text
    assert "source.decomposition_previews" in text
    assert "source.child_goal_previews" in text
    assert "machineTrace.goal_decomposition_previews" in text
    assert "machineTrace.decomposition_previews" in text
    assert "machineTrace.child_goal_previews" in text
    assert "summary.goal_decomposition_previews" in text
    assert "summary.decomposition_previews" in text
    assert "summary.child_goal_previews" in text


def test_memory_panel_reads_top_level_and_machine_trace_preview_rows():
    text = _text()

    assert "snapshot.memory_record_previews" in text
    assert "snapshot.goal_engine_memory_record_previews" in text
    assert "machineTrace.memory_record_previews" in text
    assert "machineTrace.goal_engine_memory_record_previews" in text

    assert "snapshot.memory_policy_previews" in text
    assert "snapshot.goal_engine_memory_policy_previews" in text
    assert "machineTrace.memory_policy_previews" in text
    assert "machineTrace.goal_engine_memory_policy_previews" in text

    assert "record.would_write_memory === true ? \"true\" : \"false\"" in text
    assert "policy.would_write_memory === true ? \"true\" : \"false\"" in text


def test_parent_child_panel_still_reads_preview_bundle_fields():
    text = _text()

    assert "value.orchestrator_parent_child_aggregation_previews" in text
    assert "value.parent_child_aggregation_previews" in text
    assert "value.goal_engine_parent_child_aggregation_previews" in text


def test_visibility_polish_does_not_add_execution_controls():
    block_start = _text().index("AION-GOAL-ENGINE-BOARDROOM-VISIBILITY-POLISH-V1:START")
    block_end = _text().index("AION-GOAL-ENGINE-BOARDROOM-VISIBILITY-POLISH-V1:END")
    block = _text()[block_start:block_end]

    forbidden = [
        "executeGoal",
        "runGoal",
        "createChildGoal",
        "mutateParentGoal",
        "grantPermission",
        "sendEmail",
        "writeMemory(",
        "createBooking",
        "takePayment",
    ]

    for token in forbidden:
        assert token not in block


def test_focused_suite_includes_this_lock():
    text = SUITE.read_text()
    assert "test_goal_engine_boardroom_live_preview_bundle_visibility_polish.py" in text
