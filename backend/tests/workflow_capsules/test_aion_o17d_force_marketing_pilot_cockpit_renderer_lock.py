from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o17d_force_marketing_cockpit_renderer_installed():
    text = APP.read_text(encoding="utf-8")

    assert "BEGIN AION O17D FORCE MARKETING PILOT COCKPIT RENDERER LOCK" in text
    assert "renderLiveAgentsWorkspaceBodyWithForcedMarketingCockpitO17D" in text
    assert "data-aion-o17d-forced-marketing-pilot-cockpit" in text
    assert "__debugAionO17DForceMarketingPilotCockpit" in text


def test_o17d_contains_required_visual_contract():
    text = APP.read_text(encoding="utf-8")

    assert "data-aion-o17c-marketing-pilot-cockpit" in text
    assert "data-aion-o17c-marketing-pilot-terminal" in text
    assert "aionO17CMarketingSpatialBoardroomMount" in text
    assert "data-aion-o14d-department-key=\"marketing\"" in text
    assert "Marketing Pilot Terminal · context packet" in text
    assert "background:#0f172a" in text
    assert "color:#dbeafe" in text
    assert "box-shadow:inset 4px 0 0 #0284c7" in text
