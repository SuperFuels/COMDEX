from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION BUSINESS ENDPOINT FETCH GUARD 20260630")
    end = APP_JS.index("/* END AION BUSINESS ENDPOINT FETCH GUARD 20260630 */", start)
    return APP_JS[start:end]


def test_stale_business_endpoint_fetch_guard_helpers_exist():
    block = phase_block()

    assert "function rewriteAionStaleBusinessEndpointUrl" in block
    assert "function installAionStaleBusinessEndpointFetchGuard" in block
    assert "installAionStaleBusinessEndpointFetchGuard();" in block


def test_stale_business_endpoint_fetch_guard_targets_only_business_endpoints():
    block = function_block("rewriteAionStaleBusinessEndpointUrl")

    assert "brand-foundation|boardroom|container-bindings" in block
    assert "\\/api\\/aion\\/business\\/" in block
    assert "staleBusinessEndpointPattern" in block


def test_stale_business_endpoint_fetch_guard_rejects_demo_business_ids():
    block = function_block("rewriteAionStaleBusinessEndpointUrl")

    for stale in [
        "costa-conexion",
        "costa_conexion",
        "costaconexion",
        "costa-connection",
        "costa_connection",
        "costa-conection",
        "costa_conection",
        "costa-conextion",
        "costa_conextion",
    ]:
        assert stale in block

    assert "getAionBackendBusinessEndpointId" in block
    assert "isAionLegacyDemoBusinessIdentity" in block
    assert "business_not_registered" in block


def test_fetch_guard_wraps_window_fetch_and_rewrites_before_request_leaves_app():
    block = function_block("installAionStaleBusinessEndpointFetchGuard")

    assert "window.fetch" in block
    assert "originalFetch" in block
    assert "rewriteAionStaleBusinessEndpointUrl(rawUrl)" in block
    assert "rewrittenUrl !== rawUrl" in block
    assert "Rewrote stale business endpoint id" in block
    assert "new Request(rewrittenUrl, input)" in block


def test_existing_registered_business_endpoint_resolver_still_locked():
    assert "function getAionBackendBusinessEndpointId" in APP_JS
    assert "getAionBackendBusinessEndpointId(state.workspaceId)" in APP_JS
    assert "getAionBackendBusinessEndpointId(recoveryPayload?.workspace_id || state.workspaceId)" in APP_JS
