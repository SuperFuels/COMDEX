from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22q_sticky_queue_toggle_helper_exists():
    for marker in [
        "function toggleAionPilotFollowOnQueueExpanded",
        "window.toggleAionPilotFollowOnQueueExpanded",
        "__aionPilotFollowOnQueueExpandClickHandlerInstalled",
        "data-aion-pilot-follow-on-expand",
    ]:
        assert marker in TEXT


def test_phase22q_follow_on_queue_is_sticky_footer_summary():
    start = TEXT.index("function renderAionPilotFollowOnWorkQueue")
    end = TEXT.index("window.deriveAionPilotFollowOnWorkItems", start)
    block = TEXT[start:end]

    assert "aion-pilot-follow-on-sticky" in block
    assert "Pilot task queue" in block
    assert "Current" in block
    assert "Next approval" in block
    assert "Expand tasks" in block
    assert "Collapse tasks" in block


def test_phase22q_full_task_list_only_renders_when_expanded():
    start = TEXT.index("function renderAionPilotFollowOnWorkQueue")
    end = TEXT.index("window.deriveAionPilotFollowOnWorkItems", start)
    block = TEXT[start:end]

    assert "expanded" in block
    assert "aion-pilot-follow-on-list" in block
    assert "Tick anything that must pause for human approval" in block


def test_phase22q_sticky_queue_css_installed():
    assert "PHASE 22Q LOCK: sticky follow-on mission queue" in TEXT
    assert "position: sticky !important" in TEXT
    assert "bottom: 0 !important" in TEXT
    assert "aion-pilot-follow-on-current-grid" in TEXT
