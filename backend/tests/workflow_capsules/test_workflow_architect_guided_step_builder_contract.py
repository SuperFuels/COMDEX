from __future__ import annotations

from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _read() -> str:
    assert APP_JS.exists(), "desktop/mac/src/app.js not found"
    return APP_JS.read_text(encoding="utf-8")


def test_guided_step_builder_state_exists() -> None:
    text = _read()

    assert "getWorkflowArchitectGuidedStepBuilderState" in text
    assert "setWorkflowArchitectGuidedStepBuilderState" in text
    assert "__aionWorkflowArchitectGuidedSteps" in text


def test_guided_step_builder_renders_expandable_step_cards() -> None:
    text = _read()

    assert "workflow-architect-guided-step-builder" in text
    assert "workflow-architect-step-card" in text
    assert "data-workflow-architect-add-step" in text
    assert "data-workflow-architect-remove-step" in text
    assert "data-workflow-architect-move-step" in text


def test_guided_step_builder_step_fields_are_present() -> None:
    text = _read()

    required = [
        "action",
        "source",
        "connector",
        "fields",
        "outputs",
        "approval_requirement",
    ]

    for token in required:
        assert token in text


def test_guided_step_builder_requires_user_step_approval_before_generation() -> None:
    text = _read()

    assert "stepsApproved" in text
    assert "data-workflow-architect-approve-steps" in text
    assert "Approve step list before graph generation" in text
    assert "step_list_not_approved" in text


def test_guided_step_builder_passes_steps_to_architect_review_request() -> None:
    text = _read()

    assert "workflowArchitectGuidedStepsToUserSteps" in text
    assert "user_steps:" in text
    assert "getWorkflowArchitectApprovedUserSteps" in text


def test_guided_step_builder_has_safe_default_empty_steps() -> None:
    text = _read()

    assert "steps: []" in text
    assert "stepsApproved: false" in text
    assert "provider: \"mock\"" in text
