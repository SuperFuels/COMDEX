from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")
APP = Path("desktop/mac/src/app.js")

def portrait_fn(text):
    start = text.index("function mountAionO18FRealAgentOnlyPortrait")
    end = text.index("  function updateBoardroom", start)
    return text[start:end]

def test_o18p_renderer_clean_reset_installed():
    text = RENDERER.read_text(encoding="utf-8")
    fn = portrait_fn(text)
    assert "BEGIN AION O18P REBUILD CLEAN AGENT PORTRAIT NO FRAME LOCK" in text
    assert "AION_O18P_CLEAN_AGENT_ONLY_ROOT" in fn
    assert "AION_O18P_CLEAN_REAL_AGENT_ONLY" in fn
    assert "cloneAionBoardroomAsset(\"robot_agent\")" in fn
    assert "normalizeAionBoardroomAgentModel" in fn

def test_o18p_no_overlay_or_boardroom_in_portrait_fn():
    text = RENDERER.read_text(encoding="utf-8")
    fn = portrait_fn(text).lower()
    forbidden = [
        "ringgeometry",
        "circlegeometry",
        "backdrop",
        "backglow",
        "halo",
        "labelcanvas",
        "agentroot.add(label)",
        "boardroom_table",
        "boardroom_room",
        "planargeometry(8, 8)",
    ]
    for bad in forbidden:
        assert bad not in fn

def test_o18p_app_frame_removed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18P REMOVE PORTRAIT FRAME CSS LOCK" in text
    assert "aion-o18p-remove-portrait-frame-style" in text
    assert "__debugAionO18PCleanAgentPortrait" in text
    assert "border-radius:0 !important" in text
    assert "clean_canvas" in text
