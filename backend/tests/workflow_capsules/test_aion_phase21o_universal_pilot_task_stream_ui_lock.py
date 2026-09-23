from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21o_lock_marker_exists():
    assert "PHASE 21O LOCK: Universal Pilot task stream simple dashboard" in TEXT


def test_phase21o_universal_task_helpers_exist():
    assert "function classifyAionPilotUniversalTask" in TEXT
    assert "function buildAionPilotUniversalPlan" in TEXT
    assert "function renderAionPilotSimpleTaskStream" in TEXT


def test_phase21o_not_pdf_only():
    for token in [
        "growth_social",
        "spreadsheet",
        "website_preview",
        "advertising",
        "document",
        "general_task",
    ]:
        assert token in TEXT


def test_phase21o_simple_user_labels_exist():
    for token in [
        "Ask for any business task",
        "Pilot plan",
        "Mission contract",
        "Results",
        "Pilot stream",
        "Advanced details",
    ]:
        assert token in TEXT


def test_phase21o_technical_details_are_collapsed():
    assert "renderAionPilotAdvancedTechnicalDetails" in TEXT
    assert "<details" in TEXT
    assert "proof, hashes, paths, lanes and blocked actions" in TEXT


def test_phase21o_create_draft_builds_universal_plan():
    assert "pilotState.plan = buildAionPilotUniversalPlan(requestText);" in TEXT


def test_phase21o_risky_actions_require_approval_language():
    for token in [
        "Posting publicly",
        "Sending messages or emails",
        "Spending money or running ads",
        "Deploying to production",
        "Booking, dispatching, escrow or payment actions",
    ]:
        assert token in TEXT


def test_phase21o_no_forbidden_live_buttons():
    for forbidden in [
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
    ]:
        assert forbidden not in TEXT


def test_phase21o_render_cockpit_defaults_to_simple_dashboard():
    start = TEXT.index("function renderAionPilotCockpitPanel")
    block = TEXT[start:start + 260]
    assert "return renderAionPilotSimpleTaskStream(snapshot);" in block


def test_phase21o_safety_message_still_visible():
    assert "AION stopped itself before doing anything risky." in TEXT
