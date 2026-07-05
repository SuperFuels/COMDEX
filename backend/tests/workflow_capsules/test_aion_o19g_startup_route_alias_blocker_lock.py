from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o19g_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19G STARTUP ROUTE ALIAS BLOCKER LOCK" in text
    assert "__debugAionO19GStartupRouteAliasBlocker" in text
    assert "[AION] O19G startup route alias blocker installed" in text

def test_small_business_foundation_is_not_alias_to_business_context():
    text = APP.read_text(encoding="utf-8")
    fn = text.split("function normaliseAionBusinessTabAlias", 1)[1].split("\n}", 1)[0]
    assert 'if (key === "small_business_foundation") return "small_business_foundation";' in fn
    assert 'key === "small_business_foundation" ||' not in fn

def test_small_business_foundation_allowed_as_forced_route():
    text = APP.read_text(encoding="utf-8")
    block = text.split("const allowedForcedTabs = [", 1)[1].split("];", 1)[0]
    assert '"small_business_foundation"' in block

def test_startup_helper_sets_forced_route_and_render_branch_returns_selector():
    text = APP.read_text(encoding="utf-8")
    assert 'window.localStorage?.setItem("aion.forcedMainTab.v2", "small_business_foundation");' in text
    assert 'window.__aionForcedMainTabV2 = "small_business_foundation";' in text
    assert 'if (state.activeTab === "small_business_foundation") {' in text
    assert "return renderBusinessEntryModeSelector();" in text
    assert "I have an idea" in text
    assert "I have a business" in text
