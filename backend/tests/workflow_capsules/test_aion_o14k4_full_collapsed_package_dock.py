from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14k4_full_package_renderer_exists():
    assert "getAionO14KDepartmentPackageConfig" in APP
    assert "renderAionO14KFullPackageContent" in APP
    assert "renderAionO14KCollapsedPackageDockUnderBoardroom" in APP
    assert 'data-aion-o14k-full-package-panel="true"' in APP


def test_o14k4_marketing_full_content_has_original_information():
    assert "Marketing Boardroom assignment active" in APP
    assert "boardroom_goal_sheet" in APP
    assert "marketing_pilot" in APP
    assert "workflow_goal_loop_marketing_goal_sheet" in APP
    assert "Increase business growth through coordinated department goals" in APP
    assert "Complete Marketing discovery before generating final department plan." in APP
    assert "social accounts" in APP
    assert "Marketing discovery packet" in APP
    assert "Focus Discovery" in APP
    assert "Open Linked Goal Sheet" in APP
    assert "Refresh Package" in APP


def test_o14j_fallback_dock_is_disabled():
    assert "O14J fallback collapsed dock disabled by O14K.4" in APP


def test_o14k3_cleanup_is_live_agents_only_and_protects_boardroom():
    assert "if (isBoardroomRouteO14K3()) return;" in APP
    assert "if (!isLiveAgentsRouteO14K3()) return;" in APP
    assert "hasSpatialBoardroomO14K3" in APP
    assert "isInsideCollapsedDockO14K3" in APP
    assert "data-aion-o14k3-live-agents-top-package-removed" in APP
    assert 'text.includes("Live Agents") && text.includes("SPATIAL")' in APP
