from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def test_backend_business_endpoint_resolver_exists_and_rejects_legacy_demo_identity():
    block = function_block("getAionBackendBusinessEndpointId")

    assert "getAionWorkflowBusinessContainerId" in block
    assert "getAionRegisteredBusinessIdentity" in block
    assert "isAionLegacyDemoBusinessIdentity" in block
    assert "business_not_registered" in block


def test_save_brand_foundation_uses_registered_business_endpoint_resolver():
    block = function_block("saveBrandFoundationToBackend")

    assert "getAionBackendBusinessEndpointId(state.workspaceId)" in block
    assert "`/api/aion/business/brand-foundation/${workspaceId}`" in block
    assert "const workspaceId = encodeURIComponent(state.workspaceId);" not in block


def test_load_desktop_data_business_endpoints_use_registered_business_endpoint_resolver():
    assert "getAionBackendBusinessEndpointId(recoveryPayload?.workspace_id || state.workspaceId)" in APP_JS
    assert "`/api/aion/business/brand-foundation/${recoveredWorkspaceId}`" in APP_JS
    assert "`/api/aion/business/boardroom/${recoveredWorkspaceId}`" in APP_JS
    assert "`/api/aion/business/container-bindings/${recoveredWorkspaceId}`" in APP_JS
    assert "const recoveredWorkspaceId = encodeURIComponent(\n      recoveryPayload?.workspace_id || state.workspaceId," not in APP_JS


def test_business_backend_endpoints_do_not_use_raw_stale_workspace_identity():
    forbidden_endpoint_patterns = [
        "brand-foundation/${state.workspaceId}",
        "boardroom/${state.workspaceId}",
        "container-bindings/${state.workspaceId}",
        "brand-foundation/${recoveryPayload?.workspace_id",
        "boardroom/${recoveryPayload?.workspace_id",
        "container-bindings/${recoveryPayload?.workspace_id",
        "brand-foundation/costa-conexion",
        "boardroom/costa-conexion",
        "container-bindings/costa-conexion",
    ]

    for pattern in forbidden_endpoint_patterns:
        assert pattern not in APP_JS

    assert "getAionBackendBusinessEndpointId(state.workspaceId)" in APP_JS
    assert "getAionBackendBusinessEndpointId(recoveryPayload?.workspace_id || state.workspaceId)" in APP_JS
