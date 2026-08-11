from pathlib import Path


APP = Path(
    "desktop/mac/src/app.js"
).read_text(encoding="utf-8")


def function_block(name: str) -> str:
    start = APP.index(f"function {name}")
    brace = APP.index("{", start)

    depth = 0
    quote = ""
    escaped = False

    for index in range(brace, len(APP)):
        char = APP[index]

        if quote:
            if escaped:
                escaped = False
                continue

            if char == "\\":
                escaped = True
                continue

            if char == quote:
                quote = ""

            continue

        if char in {"'", '"', "`"}:
            quote = char
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                return APP[start:index + 1]

    raise AssertionError(
        f"Could not extract function {name}"
    )


def test_o25ay_startup_owner_is_one_shot_per_page_load():
    block = function_block(
        "applyAionO25ABFreshStartupRouteOwner"
    )

    assert "__aionO25ABStartupRouteClaimed" in block
    assert "startupRouteAlreadyClaimed" in block
    assert "if (!startupRouteAlreadyClaimed)" in block
    assert "one_shot_startup_owner" in block


def test_o25ay_fresh_launch_clears_stale_persisted_routes():
    block = function_block(
        "applyAionO25ABFreshStartupRouteOwner"
    )

    for key in (
        "aion.activeTab",
        "aion.activeTab.v1",
        "aion.lastActiveTab.v1",
        "aion.forcedMainTab.v2",
    ):
        assert key in block

    assert (
        'state.activeTab =\n'
        '          "small_business_foundation";'
        in block
    )


def test_o25ay_finance_handoff_remains_first_render_exception():
    block = function_block(
        "applyAionO25ABFreshStartupRouteOwner"
    )

    assert "financeHandoffActive" in block
    assert "aion.businessTwin.financeHandoffActive.v1" in block
    assert "financeHandoffActive && !startupRouteAlreadyClaimed" in block
    assert "completedBusinessPacket && !startupRouteAlreadyClaimed" in block
    assert 'state.activeTab = "live_agents"' in block
    assert '"finance"' in block


def test_o25ay_legacy_marketing_stream_route_redirects_to_unified_department():
    start = APP.index(
        "function renderMainSurface()"
    )
    end = APP.index(
        "function buildLiveAgentCards",
        start,
    )
    block = APP[start:end]

    assert '"marketing_stream"' in block
    assert (
        'if (state.activeTab === "marketing_stream")'
        in block
    )
    assert 'state.activeTab = "live_agents";' in block
    assert 'state.selectedLiveAgentDepartment = "marketing";' in block
    assert "return renderLiveAgentsSurface();" in block


def test_o25ay_canonical_compatibility_mapping_keeps_old_links_recoverable():
    assert (
        'marketing_stream: "marketing_stream"'
        in APP
    )

    assert (
        '"marketing_stream",'
        in APP
    )
    app_tabs = APP[APP.index("const APP_TABS"):APP.index("/*", APP.index("const APP_TABS"))]
    assert '{ key: "marketing_stream", label: "Marketing Stream" }' not in app_tabs


def test_o25ay_startup_selector_has_distinct_route():
    assert (
        'if (state.activeTab === '
        '"small_business_foundation")'
        in APP
    )

    assert (
        "return renderBusinessEntryModeSelector();"
        in APP
    )
