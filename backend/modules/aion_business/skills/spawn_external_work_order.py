from __future__ import annotations

import secrets

from backend.modules.aion_business.contracts.skills import SkillRunRequest, SkillRunResult
from backend.modules.aion_business.contracts.tasks import ExternalWorkOrder
from backend.modules.aion_business.skills.base import (
    BaseSkill,
    SkillValidationError,
)


class SpawnExternalWorkOrderSkill(BaseSkill):
    """
    Create a structured external work order for delegated specialist execution.

    This skill does not execute the external work.
    It only creates the normalized work-order artifact that later orchestration
    layers can route to coding agents, browser agents, spreadsheet agents, etc.
    """

    @property
    def skill_id(self) -> str:
        return "spawn_external_work_order"

    def validate_request(self, request: SkillRunRequest) -> None:
        super().validate_request(request)

        payload = request.input_payload

        for field in ["provider", "capability", "objective"]:
            value = payload.get(field)
            if not value or not isinstance(value, str):
                raise SkillValidationError(f"missing_{field}")

        for field in ["business_context", "task_context", "metadata"]:
            value = payload.get(field)
            if value is not None and not isinstance(value, dict):
                raise SkillValidationError(f"{field}_must_be_object")

        for field in ["allowed_tools", "acceptance_criteria"]:
            value = payload.get(field)
            if value is not None and not isinstance(value, list):
                raise SkillValidationError(f"{field}_must_be_list")

        budget_limit = payload.get("budget_limit")
        if budget_limit is not None:
            try:
                budget_value = float(budget_limit)
            except Exception as exc:
                raise SkillValidationError("invalid_budget_limit") from exc
            if budget_value < 0:
                raise SkillValidationError("negative_budget_limit")

        output_contract = payload.get("output_contract")
        if output_contract is not None and not isinstance(output_contract, str):
            raise SkillValidationError("output_contract_must_be_string")

        escalation_policy = payload.get("escalation_policy")
        if escalation_policy is not None and not isinstance(escalation_policy, str):
            raise SkillValidationError("escalation_policy_must_be_string")

    def run(self, request: SkillRunRequest) -> SkillRunResult:
        payload = request.input_payload

        work_order = ExternalWorkOrder(
            id=f"ewo-{secrets.token_hex(6)}",
            parent_task_id=request.task_id,
            provider=str(payload["provider"]),
            capability=str(payload["capability"]),
            objective=str(payload["objective"]),
            business_context=dict(payload.get("business_context", {})),
            task_context=dict(payload.get("task_context", {})),
            allowed_tools=list(payload.get("allowed_tools", [])),
            acceptance_criteria=list(payload.get("acceptance_criteria", [])),
            budget_limit=float(payload.get("budget_limit", 0.0)),
            output_contract=payload.get("output_contract"),
            trace_required=bool(payload.get("trace_required", True)),
            escalation_policy=payload.get("escalation_policy"),
        )

        metadata = dict(payload.get("metadata", {}))

        return SkillRunResult(
            ok=True,
            skill_id=self.skill_id,
            output_payload={
                "work_order": work_order.model_dump(mode="json"),
                "work_order_id": work_order.id,
                "provider": work_order.provider,
                "capability": work_order.capability,
                "objective": work_order.objective,
                "metadata": metadata,
            },
            artifacts=[],
            warnings=[],
            error_code=None,
            trace={
                "provider": work_order.provider,
                "capability": work_order.capability,
                "budget_limit": work_order.budget_limit,
                "trace_required": work_order.trace_required,
            },
            side_effects_applied=False,
        )