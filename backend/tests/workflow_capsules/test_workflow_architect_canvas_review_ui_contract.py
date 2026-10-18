from __future__ import annotations

from pathlib import Path


PANEL = Path("frontend/src/glyphnet/components/workflow-architect/WorkflowArchitectReviewPanel.tsx")
INDEX = Path("frontend/src/glyphnet/components/workflow-architect/index.ts")


def _read_panel() -> str:
    assert PANEL.exists(), f"missing Workflow Architect review panel: {PANEL}"
    return PANEL.read_text(encoding="utf-8")


def test_workflow_architect_review_panel_exists_and_exports() -> None:
    text = _read_panel()

    assert INDEX.exists()
    assert "WorkflowArchitectReviewPanel" in text
    assert "export default WorkflowArchitectReviewPanel" in text


def test_workflow_architect_review_panel_calls_client_bridge() -> None:
    text = _read_panel()

    assert "buildWorkflowArchitectReview" in text
    assert "workflow-architect-build-review-button" in text
    assert "workflow-architect-review-result" in text


def test_workflow_architect_review_panel_shows_steps_errors_and_warnings() -> None:
    text = _read_panel()

    assert "workflow-architect-generated-steps" in text
    assert "workflow-architect-errors" in text
    assert "workflow-architect-warnings" in text


def test_workflow_architect_review_panel_blocks_canvas_load_until_valid() -> None:
    text = _read_panel()

    assert "reviewIsCanvasLoadable" in text
    assert "canLoadToCanvas" in text
    assert "workflow-architect-load-canvas-button" in text
    assert "workflow-architect-load-blocked" in text
    assert "onValidReview" in text


def test_workflow_architect_review_panel_preserves_safety_rules() -> None:
    text = _read_panel().lower()

    assert "do not live-send gmail messages" in text
    assert "do not bypass human approval" in text
    assert "do not invent unsupported aion node types" in text

    forbidden_runtime_tokens = [
        "users.messages.send",
        "gmail_live_send",
        "send_message(",
        "live_execute",
    ]

    assert "forbidden" in text
    assert "reviewiscanvasloadable" in text
    assert "fetch(" not in text

    for token in forbidden_runtime_tokens:
        assert token in text
