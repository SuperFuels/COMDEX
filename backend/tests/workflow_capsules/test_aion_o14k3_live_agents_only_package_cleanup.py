from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14k2_global_remover_is_disabled():
    assert "O14K.2 disabled by O14K.3" in APP
    assert "global div/section package removal was too broad" in APP


def test_o14k3_cleanup_is_live_agents_only():
    assert "BEGIN AION O14K3 LIVE-AGENTS-ONLY PACKAGE DOCK CLEANUP" in APP
    assert 'activeTabKeyO14K3() === "live_agents"' in APP
    assert 'activeTabKeyO14K3() === "boardroom"' in APP
    assert "if (isBoardroomRouteO14K3()) return;" in APP
    assert "if (!isLiveAgentsRouteO14K3()) return;" in APP


def test_o14k3_does_not_scan_generic_div_or_section_nodes():
    block = APP.split("BEGIN AION O14K3 LIVE-AGENTS-ONLY PACKAGE DOCK CLEANUP", 1)[1]
    block = block.split("END AION O14K3 LIVE-AGENTS-ONLY PACKAGE DOCK CLEANUP", 1)[0]
    assert "'section'" not in block
    assert "'div'" not in block
    assert "section," not in block
    assert "div," not in block


def test_o14k3_preserves_collapsed_dock_content():
    assert "isInsideCollapsedDockO14K3" in APP
    assert '[data-aion-o14k-collapsed-package-dock="true"]' in APP
    assert '[data-aion-o14k-package-content="true"]' in APP
    assert "window.removeLiveAgentsTopPackageDocksO14K3" in APP
