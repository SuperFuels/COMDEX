from pathlib import Path

RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")
APP = Path("desktop/mac/src/app.js")

def portrait_fn(text):
    start = text.index("function mountAionO18FRealAgentOnlyPortrait")
    end = text.index("  function updateBoardroom", start)
    return text[start:end]

def test_o18k_clean_portrait_renderer_installed():
    text = RENDERER.read_text(encoding="utf-8")
    fn = portrait_fn(text)
    assert "BEGIN AION O18K CLEAN REAL AGENT PORTRAIT RENDERER LOCK" in text
    assert "AION_O18K_CLEAN_REAL_AGENT_PORTRAIT_ROOT" in fn
    assert "AION_O18K_CLEAN_REAL_ROBOT_AGENT_ONLY_PORTRAIT" in fn
    assert "cloneAionBoardroomAsset(\"robot_agent\")" in fn
    assert "normalizeAionBoardroomAgentModel" in fn

def test_o18k_portrait_has_no_overlay_objects():
    text = RENDERER.read_text(encoding="utf-8")
    fn = portrait_fn(text)
    assert "RingGeometry" not in fn
    assert "halo" not in fn.lower()
    assert "backGlow" not in fn
    assert "agentRoot.add(label)" not in fn
    assert "boardroom_table" not in fn
    assert "boardroom_room" not in fn

def test_o18k_app_css_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18K CLEAN PORTRAIT FRAME CSS LOCK" in text
    assert "aion-o18k-clean-portrait-frame-style" in text
    assert "__debugAionO18KCleanPortrait" in text
    assert "clean_canvas" in text
