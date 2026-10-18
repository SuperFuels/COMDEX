from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o17c_marketing_pilot_cockpit_installed():
    text = APP.read_text(encoding="utf-8")

    assert "BEGIN AION O17C MARKETING PILOT COCKPIT BOARDROOM TERMINAL LOCK" in text
    assert "data-aion-o17c-marketing-pilot-cockpit" in text
    assert "data-aion-o17c-marketing-pilot-terminal" in text
    assert "Marketing Pilot Terminal · context packet" in text
    assert "data-aion-o17c-marketing-terminal-input" in text
    assert "data-aion-o17c-marketing-terminal-voice" in text


def test_o17c_uses_boardroom_terminal_visual_contract():
    text = APP.read_text(encoding="utf-8")

    assert "data-aion-council-session-terminal" in text
    assert "data-aion-council-terminal-header" in text
    assert "background:#0f172a" in text
    assert "color:#dbeafe" in text
    assert "box-shadow:inset 4px 0 0 #0284c7" in text
    assert "Marketing Context Packet" in text
    assert "Execution boundary: approval_gated" in text


def test_o17c_keeps_spatial_marketing_boardroom_and_hides_legacy_noise():
    text = APP.read_text(encoding="utf-8")

    assert "aionO17CMarketingSpatialBoardroomMount" in text
    assert "data-aion-o14d-department-121-spatial-boardroom-mount" in text
    assert "data-aion-o14d-department-key=\"marketing\"" in text
    assert "data-aion-o17c-marketing-cockpit-hidden-compat" in text
    assert "renderLiveAgentsWorkspaceBodyWithMarketingCockpitO17C" in text


def test_o17c_writes_to_department_intelligence_and_safe_queue():
    text = APP.read_text(encoding="utf-8")

    assert "aion.departmentIntelligence.marketing" in text
    assert "writeMarketingLedgerO17C" in text
    assert "buildMarketingPlanO17C" in text
    assert "buildMarketingQueueO17C" in text
    assert "runNextMarketingSafeTaskO17C" in text
    assert "live_external_actions_blocked: true" in text
    assert "preview_only_no_external_write" in text
