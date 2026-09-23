from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")


def test_boardroom_visibility_mount_audit_patch_exists():
    text = APP.read_text()

    assert "AION-GOAL-ENGINE-BOARDROOM-VISIBILITY-MOUNT-AUDIT-V1:START" in text
    assert "function renderAionGoalEngineBoardroomVisibilityMountAuditV1" in text
    assert 'data-aion-goal-engine-visibility-mount-audit="v1"' in text


def test_boardroom_visibility_mounts_required_read_only_panels():
    text = APP.read_text()

    for token in [
        "renderAionGoalEngineEvidencePointerViewerV1",
        "renderAionGoalEngineVariantComparisonViewerV1",
        "renderAionGoalEngineProviderCapabilityManifestV1",
        "renderAionGoalEngineContainerProjectionV1",
        "renderAionGoalEngineProviderAuditPanelV1",
        "renderAionGoalEngineMemoryRuntimePanelV1",
    ]:
        assert token in text


def test_provider_audit_panel_is_visible_but_read_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineProviderAuditPanelV1"):
        text.index("function renderAionGoalEngineMemoryRuntimePanelV1")
    ]

    assert 'data-aion-goal-engine-provider-audit="v1"' in block
    assert "provider_audit" in block
    assert "external_writes" in block
    assert "business_state_mutation" in block
    assert "<button" not in block
    assert ".send(" not in block
    assert "fetch(" not in block


def test_memory_runtime_panel_is_visible_but_read_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineMemoryRuntimePanelV1"):
        text.index("function renderAionGoalEngineBoardroomVisibilityMountAuditV1")
    ]

    assert 'data-aion-goal-engine-memory-runtime="v1"' in block
    assert "memory_runtime_summary" in block
    assert "write_guard" in block
    assert "read_guard" in block
    assert "<button" not in block
    assert ".send(" not in block
    assert "fetch(" not in block


def test_visibility_mount_css_exists():
    text = CSS.read_text()

    assert "AION-GOAL-ENGINE-BOARDROOM-VISIBILITY-MOUNT-AUDIT-CSS-V1:START" in text
    assert ".aion-boardroom-goal-engine-visibility-audit" in text
    assert ".aion-boardroom-provider-audit-panel" in text
    assert ".aion-boardroom-memory-runtime-panel" in text

def test_visibility_audit_is_directly_mounted_in_real_runtime_preview_renderer():
    text = APP.read_text()
    start = text.index("function renderAionGoalEngineVisibleBoardroomPanelsV1")
    end = text.index("function renderBoardroomDashboardView", start)
    block = text[start:end]

    assert "renderAionGoalEngineBoardroomVisibilityMountAuditV1(source)" in block
    assert "${panels}" in block

