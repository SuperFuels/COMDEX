from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_local_node_runtime_keeps_its_route_but_uses_user_facing_language():
    assert '{ key: "local_node", label: "Local processing" }' in APP
    assert 'data-aion-local-processing-page="true"' in APP
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


def test_local_processing_has_a_clear_sidebar_icon_and_responsive_styles():
    assert "aion-sidebar-local-processing-icon" in APP
    assert 'style.id = "aion-local-processing-styles-v1"' in APP
    assert ".aion-local-processing-metrics" in APP
    assert "@media(max-width:720px)" in APP

