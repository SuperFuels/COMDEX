from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text()


def test_phase23s_has_queue_normalisation_helpers():
    assert "function normaliseAionPilotMissionPreviewQueues" in TEXT
    assert "function applyAionPilotMissionPreviewQueuesToState" in TEXT
    assert "department_route" in TEXT
    assert "department_queue" in TEXT
    assert "tool_execution_queue" in TEXT
    assert "tool_execution_summary" in TEXT


def test_phase23s_renders_department_queue_summary():
    assert "function renderAionPilotDepartmentQueueSummary" in TEXT
    assert "data-aion-pilot-department-queue-summary" in TEXT
    assert "Department execution queue" in TEXT
    assert "Queue hashes and proof" in TEXT


def test_phase23s_renders_department_lanes_for_business_functions():
    for department in [
        "marketing",
        "sales",
        "finance",
        "operations",
        "support",
        "builder",
        "pilot",
    ]:
        assert department in TEXT

    assert "data-aion-pilot-department-lane" in TEXT


def test_phase23s_pilot_stream_includes_queue_summary_after_outputs():
    start = TEXT.find("function renderAionPilotSimpleTaskStream")
    assert start >= 0
    end = TEXT.find("\\n/* END PHASE 21R LOCK */", start)
    block = TEXT[start:end if end > 0 else len(TEXT)]

    assert "renderAionPilotStepOutputCards(pilotState)" in block
    assert "renderAionPilotDepartmentQueueSummary(pilotState)" in block
    assert "renderAionPilotFollowOnWorkQueue(plan, pilotState)" in block


def test_phase23s_counts_ready_staged_waiting_and_blocked():
    assert "Ready ${escapeHtml(String(readyCount))}" in TEXT
    assert "Staged ${escapeHtml(String(stagedCount))}" in TEXT
    assert "Needs approval ${escapeHtml(String(waitingApprovalCount))}" in TEXT
    assert "Blocked ${escapeHtml(String(blockedCount))}" in TEXT
