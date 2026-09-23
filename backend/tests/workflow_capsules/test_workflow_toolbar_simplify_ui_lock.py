from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _src() -> str:
    return APP.read_text(encoding="utf-8")


def _patch() -> str:
    src = _src()
    marker = "AION PATCH: Workflow Toolbar Simplify v15"
    assert marker in src
    return src.split(marker, 1)[1]


def test_toolbar_simplify_patch_installed():
    patch = _patch()

    assert "window.__aionWorkflowToolbarSimplifyV15Installed" in patch
    assert "window.__debugAionWorkflowToolbarSimplifyV15" in patch
    assert "aion-workflow-toolbar-simplify-v15-style" in patch


def test_obsolete_toolbar_controls_are_hidden():
    patch = _patch()

    assert '[data-aion-workflow-save="true"]' in patch
    assert '[title="Save workflow"]' in patch
    assert '[data-aion-canvas-mode="workflow"]' in patch
    assert '[title="Workflow Canvas"]' in patch
    assert '[data-aion-master-glyph-clear-staged="true"]' in patch
    assert '[title="Clear staged glyph nodes"]' in patch

    assert "display: none !important" in patch
    assert "pointer-events: none !important" in patch


def test_useful_toolbar_controls_are_preserved():
    patch = _patch()

    assert "Workflow Glyph Library" in patch
    assert "Add next step" in patch

    hidden_css = patch.split("style.textContent", 1)[1].split("`;", 1)[0]
    assert "Workflow Glyph Library" not in hidden_css
    assert "Add next step" not in hidden_css
    assert "Publish workflow" not in hidden_css
    assert "Execute workflow safely" not in hidden_css


def test_no_dangerous_runtime_loops_or_observers():
    patch = _patch()

    assert "MutationObserver" not in patch
    assert "setInterval" not in patch
    assert "requestRender =" not in patch
