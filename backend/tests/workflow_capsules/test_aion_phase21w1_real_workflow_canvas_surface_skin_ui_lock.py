from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21w1_marker_exists():
    assert "PHASE 21W.1 LOCK: Real workflow canvas surface fax skin" in TEXT
    assert "installAionRealWorkflowCanvasSurfaceFaxSkinV21W1" in TEXT


def test_phase21w1_targets_real_canvas_classes():
    for token in [
        ".operations-agents-surface .aion-workflow-canvas-shell",
        ".operations-agents-surface .aion-workflow-topbar",
        ".operations-agents-surface .aion-workflow-sidebar",
        ".operations-agents-surface .aion-workflow-inspector",
        ".operations-agents-surface .aion-workflow-canvas",
        ".operations-agents-surface .aion-workflow-floating-toolbar",
    ]:
        assert token in TEXT


def test_phase21w1_restores_grid():
    assert "--aion-fax-grid" in TEXT
    assert "linear-gradient(var(--aion-fax-grid) 1px, transparent 1px)" in TEXT
    assert "background-size: 28px 28px" in TEXT


def test_phase21w1_no_execution_logic_added():
    start = TEXT.index("PHASE 21W.1 LOCK: Real workflow canvas surface fax skin")
    end = TEXT.index("END PHASE 21W.1 REAL WORKFLOW CANVAS SURFACE FAX SKIN", start)
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
