from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")
APP = Path("desktop/mac/src/app.js")

def test_o18f_renderer_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "BEGIN AION O18F REAL AGENT ONLY PORTRAIT RENDERER LOCK" in text
    assert "function mountAionO18FRealAgentOnlyPortrait" in text
    assert "AION_O18F_REAL_ROBOT_AGENT_ONLY_PORTRAIT" in text
    assert "cloneAionBoardroomAsset(\"robot_agent\")" in text
    assert "normalizeAionBoardroomAgentModel" in text

def test_o18f_department_121_routes_to_portrait_renderer():
    text = RENDERER.read_text(encoding="utf-8")
    assert "o18fIsDepartment121" in text
    assert "o18fCameraMode.endsWith(\"_121\")" in text
    assert "return mountAionO18FRealAgentOnlyPortrait(container, options || {})" in text

def test_o18f_normal_export_kept():
    text = RENDERER.read_text(encoding="utf-8")
    assert "mountBoardroom," in text
    assert "updateBoardroom," in text
    assert "mountAionO18FRealAgentOnlyPortrait," in text

def test_o18f_app_facetime_frame_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18F FACETIME FRAME CLEANUP LOCK" in text
    assert "aion-o18f-facetime-frame-cleanup-style" in text
    assert "__debugAionO18FFaceTimeFrame" in text
    assert "MARKETING AGENT · LIVE" in text
