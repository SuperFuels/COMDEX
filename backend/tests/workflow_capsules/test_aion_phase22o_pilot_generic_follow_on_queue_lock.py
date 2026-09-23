from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22o_generic_follow_on_helpers_exist():
    for marker in [
        "function deriveAionPilotFollowOnWorkItems",
        "function classifyAionPilotFollowOnWorkItem",
        "function renderAionPilotFollowOnWorkQueue",
        "window.deriveAionPilotFollowOnWorkItems",
        "window.renderAionPilotFollowOnWorkQueue",
    ]:
        assert marker in TEXT


def test_phase22o_follow_on_queue_mounts_after_output():
    start = TEXT.index("function renderAionPilotSimpleTaskStream")
    end = TEXT.index("function renderAionPilotAdvancedTechnicalDetails", start)
    block = TEXT[start:end]

    assert "renderAionPilotStepOutputCards(pilotState)" in block
    assert "renderAionPilotFollowOnWorkQueue(plan, pilotState)" in block


def test_phase22o_follow_on_queue_is_generic_not_home_fixed_specific():
    start = TEXT.index("function deriveAionPilotFollowOnWorkItems")
    end = TEXT.index("function renderAionPilotFollowOnWorkQueue", start)
    block = TEXT[start:end]

    forbidden = [
        "Home Fixed",
        "business plan draft",
        "roof repairs",
        "Google Business Profile",
        "Facebook posts",
        "WhatsApp-first",
    ]

    for marker in forbidden:
        assert marker not in block


def test_phase22o_follow_on_queue_classifies_approval_vs_safe_draft():
    start = TEXT.index("function classifyAionPilotFollowOnWorkItem")
    end = TEXT.index("function getAionPilotFollowOnApprovalStages", start)
    block = TEXT[start:end]

    assert "needs_approval" in block
    assert "safe_draft" in block
    for approval_signal in ["publish", "send ", "spend", "payment", "book", "deploy", "account", "live"]:
        assert approval_signal in block


def test_phase22o_follow_on_queue_has_visible_approval_toggles_and_continue_action():
    start = TEXT.index("function renderAionPilotFollowOnWorkQueue")
    end = TEXT.index("window.deriveAionPilotFollowOnWorkItems", start)
    block = TEXT[start:end]

    assert "Pilot task queue" in block
    assert "data-aion-pilot-follow-on-approval-toggle" in block
    assert "Needs approval" in block
    assert "Safe draft work" in block
    assert "Continue safe work" in block


def test_phase22o_follow_on_click_handler_and_css_exist():
    assert "__aionPilotFollowOnApprovalClickHandlerInstalled" in TEXT
    assert 'closest?.("[data-aion-pilot-follow-on-approval-toggle]")' in TEXT
    assert "PHASE 22O LOCK: generic follow-on work queue" in TEXT
    assert "aion-pilot-follow-on-row" in TEXT
