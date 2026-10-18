from __future__ import annotations

from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _read_app_js() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js must exist"
    return APP_JS.read_text(encoding="utf-8")


def test_desktop_canvas_has_save_as_workflow_capsule_button() -> None:
    text = _read_app_js()

    assert 'data-aion-workflow-save-capsule="true"' in text
    assert "Save as Workflow Capsule" in text


def test_desktop_canvas_posts_to_canvas_compile_save_api() -> None:
    text = _read_app_js()

    assert "/api/workflow-capsules/canvas/compile-save" in text
    assert "saveAionWorkflowCanvasAsCapsule" in text
    assert "buildAionWorkflowCanvasCapsulePayload" in text


def test_desktop_canvas_capsule_bridge_is_compile_save_only() -> None:
    text = _read_app_js()

    start = text.index("async function saveAionWorkflowCanvasAsCapsule")
    end = text.index("function renderAionWorkflowGlyphDebugExecutionPanel", start)
    block = text[start:end]

    assert "compile-save" in block
    assert "executed" not in block.lower()
    assert "/run-dry" not in block
    assert "resume" not in block.lower()
    assert "approve" not in block.lower()
    assert "send" not in block.lower()


def test_desktop_canvas_capsule_payload_uses_vault_handles_not_credentials() -> None:
    text = _read_app_js()

    start = text.index("function buildAionWorkflowCanvasCapsulePayload")
    end = text.index("async function saveAionWorkflowCanvasAsCapsule", start)
    block = text[start:end]

    assert "vault.gmail.credentials" in block
    assert "access_token" not in block
    assert "refresh_token" not in block
    assert "client_secret" not in block
    assert "password" not in block
