from __future__ import annotations

from backend.modules.business_runtime.contracts_operator import AgentOperator, OperatorState


def build_marketing_operator_v1() -> AgentOperator:
    return AgentOperator(
        id="operator_marketing_v1",
        name="Marketing Operator v1",
        department_key="marketing",
        mission="Draft and queue marketing content for review.",
        capability_ids=[
            "draft_marketing_copy",
            "draft_carousel_content",
            "attach_connector_context",
            "request_approval",
        ],
        workflow_ids=["workflow_marketing_content_draft_v1"],
        state=OperatorState.ACTIVE,
    )