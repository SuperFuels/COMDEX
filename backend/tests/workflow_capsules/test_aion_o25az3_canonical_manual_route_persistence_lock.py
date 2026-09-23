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


def test_o25az3_marketing_is_allowed_by_early_manual_route_owner():
    start = APP.index(
        "function renderMainSurface()"
    )
    end = APP.index(
        "function buildLiveAgentCards",
        start,
    )
    block = APP[start:end]

    allowlist_start = block.index(
        "const allowedForcedTabs"
    )
    allowlist_end = block.index(
        "];",
        allowlist_start,
    )
    allowlist = block[
        allowlist_start:allowlist_end
    ]

    assert '"marketing_stream"' in allowlist
    assert '"live_agents"' in allowlist
    assert '"small_business_foundation"' in allowlist


def test_o25az3_sidebar_sets_requested_tab_in_runtime_state():
    block = function_block(
        "setAionSidebarActiveTabHardV1"
    )

    assert "state.activeTab = tab" in block
    assert "window.__aionForcedMainTabV2 = tab" in block
    assert "window.__aionLastManualNavTabV2 = tab" in block


def test_o25az3_sidebar_persists_all_route_keys():
    block = function_block(
        "setAionSidebarActiveTabHardV1"
    )

    for key in (
        "aion.activeTab",
        "aion.activeTab.v1",
        "aion.lastActiveTab.v1",
        "aion.forcedMainTab.v2",
        "aionDesktop.activeTab",
    ):
        assert key in block


def test_o25az3_manual_navigation_releases_startup_owner():
    block = function_block(
        "setAionSidebarActiveTabHardV1"
    )

    assert (
        "window.__aionO25ABStartupRouteClaimed = true"
        in block
    )
    assert (
        "window.__aionO25AYStartupRouteClaimed = true"
        in block
    )
    assert (
        "window.__aionManualSidebarRouteClaimedV1 = tab"
        in block
    )


def test_o25az3_sidebar_persists_desktop_store_cache():
    block = function_block(
        "setAionSidebarActiveTabHardV1"
    )

    assert "desktopStore.persistCache" in block
    assert "desktopStore.persistCacheSoon" in block


def test_o25az3_marketing_renderer_remains_canonical():
    start = APP.index(
        "function renderMainSurface()"
    )
    end = APP.index(
        "function buildLiveAgentCards",
        start,
    )
    block = APP[start:end]

    assert (
        'if (state.activeTab === "marketing_stream")'
        in block
    )
    assert "renderMarketingStreamSurface()" in block
