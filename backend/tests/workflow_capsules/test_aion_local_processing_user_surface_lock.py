from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_local_processing_is_a_business_subtab_not_a_sidebar_route():
    assert '{ key: "local_node", label: "Local processing" }' not in APP
    assert '["local_processing", "Local Processing"]' in APP
    assert 'subtabHtml = renderBusinessLocalProcessingSubtabContent();' in APP
    assert 'data-aion-local-processing-page="true"' in APP
    assert 'function renderLocalNodeSurface()' not in APP
    assert 'if (state.activeTab === "local_node")' not in APP
    assert "Local Node Status Panel" not in APP
    assert "Mac local node control surface" not in APP
    assert "Tessaris keeps the business runtime, approvals and private working data on this Mac" in APP


def test_technical_controls_and_raw_status_are_collapsed_by_default():
    assert '<details class="aion-local-processing-advanced">' in APP
    assert "Advanced technical details" in APP
    assert '<details class="aion-local-processing-raw">' in APP
    assert "Raw diagnostic status" in APP
    assert 'id="schedulerStartBtn"' in APP
    assert 'id="pauseNodeBtn"' in APP


def test_workspace_mismatch_is_explained_and_actionable():
    assert "workspaceMismatch" in APP
    assert "This Mac is linked to a different business workspace" in APP
    assert 'id="bindWorkspaceBtn"' in APP
    assert "Update the link before relying on new automated work" in APP


def test_local_processing_keeps_responsive_styles_without_sidebar_chrome():
    assert "aion-sidebar-local-processing-icon" not in APP
    assert 'style.id = "aion-local-processing-styles-v1"' in APP
    assert ".aion-local-processing-metrics" in APP
    assert "@media(max-width:720px)" in APP


def test_stale_local_processing_routes_migrate_into_business():
    assert 'activeRoute === "local_node" || forcedRoute === "local_node"' in APP
    assert 'state.activeTab = "business_context";' in APP
    assert 'state.activeBusinessContextSubtab = "local_processing";' in APP
    assert 'local_node: "business_context"' in APP
