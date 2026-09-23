from __future__ import annotations

from backend.modules.business_runtime.contracts_workflow import (
    WorkflowDefinition,
    WorkflowExecutionMode,
    WorkflowStepDefinition,
    WorkflowStepKind,
)


def build_marketing_content_draft_workflow(operator_id: str) -> WorkflowDefinition:
    return WorkflowDefinition(
        id="workflow_marketing_content_draft_v1",
        name="Marketing Content Draft v1",
        department_key="marketing",
        operator_id=operator_id,
        version="v1",
        execution_mode=WorkflowExecutionMode.DRAFT_AND_APPROVAL,
        steps=[
            WorkflowStepDefinition(
                id="step_create_brief",
                label="Create content brief",
                kind=WorkflowStepKind.CREATE_BRIEF,
            ),
            WorkflowStepDefinition(
                id="step_draft_caption",
                label="Draft caption",
                kind=WorkflowStepKind.DRAFT_CAPTION,
            ),
            WorkflowStepDefinition(
                id="step_draft_carousel",
                label="Draft carousel structure",
                kind=WorkflowStepKind.DRAFT_CAROUSEL,
            ),
            WorkflowStepDefinition(
                id="step_attach_connector_context",
                label="Attach connector context",
                kind=WorkflowStepKind.ATTACH_CONNECTOR_CONTEXT,
                config={"connector_key": "meta_facebook"},
            ),
            WorkflowStepDefinition(
                id="step_request_approval",
                label="Request approval",
                kind=WorkflowStepKind.REQUEST_APPROVAL,
            ),
            WorkflowStepDefinition(
                id="step_complete_run",
                label="Complete run",
                kind=WorkflowStepKind.COMPLETE_RUN,
            ),
        ],
    )