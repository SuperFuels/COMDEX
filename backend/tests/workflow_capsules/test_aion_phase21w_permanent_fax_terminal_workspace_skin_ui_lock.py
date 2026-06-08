from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21w_lock_markers_exist():
    assert "PHASE 21W LOCK: Permanent fax terminal AION workspace skin" in TEXT
    assert "PHASE 21W LOCK: Permanent white AION workspace background" in TEXT
    assert "PHASE 21W LOCK: Permanent fax terminal workflow canvas skin" in TEXT


def test_phase21w_temp_design_markers_removed():
    assert "TEMP DESIGN TEST: Phase 21V fax terminal Pilot skin" not in TEXT
    assert "TEMP DESIGN TEST: Phase 21V2 white Live Agents Pilot background" not in TEXT


def test_phase21w_permanent_installers_exist():
    for token in [
        "installAionFaxTerminalWorkspaceSkinV21W",
        "installAionWhiteWorkspaceBackgroundV21W",
        "installAionWorkflowFaxTerminalSkinV21W",
    ]:
        assert token in TEXT


def test_phase21w_white_background_tokens_exist():
    for token in [
        "--aion-ink-bg: #ffffff",
        "--aion-ink-paper: #ffffff",
        "--pilot-fax-paper: #ffffff",
        "background: #ffffff !important",
    ]:
        assert token in TEXT


def test_phase21w_workflow_canvas_targets_exist():
    for token in [
        ".aion-workflow-canvas-shell",
        ".aion-workflow-canvas",
        ".aion-workflow-canvas-viewport",
        ".aion-workflow-floating-toolbar",
        "[data-aion-workflow-node-id]",
        ".aion-workflow-node-card",
        ".aion-workflow-inspector",
    ]:
        assert token in TEXT


def test_phase21w_colour_language_exists():
    for token in [
        "--aion-fax-blue",
        "--aion-fax-green",
        "--aion-fax-yellow",
        "--aion-fax-red",
        "--pilot-fax-blue",
        "--pilot-fax-green",
        "--pilot-fax-yellow",
        "--pilot-fax-red",
    ]:
        assert token in TEXT


def test_phase21w_canvas_header_exists():
    assert "AION WORKFLOW — CANVAS MODE" in TEXT
    assert "AION PILOT — MISSION MODE" in TEXT


def test_phase21w_no_execution_logic_added():
    start = TEXT.index("PHASE 21W LOCK: Permanent fax terminal workflow canvas skin")
    end = TEXT.index("END PHASE 21W WORKFLOW CANVAS SKIN", start)
    block = TEXT[start:end]

    for forbidden in [
        "fetch(",
        "apiPost(",
        "sendEmail(",
        "deploySite(",
        "createPayment(",
        "stripe.",
        "revolut.",
    ]:
        assert forbidden not in block
