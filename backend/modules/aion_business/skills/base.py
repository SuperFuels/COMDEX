from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.modules.aion_business.contracts.skills import SkillRunRequest, SkillRunResult


class SkillError(Exception):
    """Base exception for all Aion Business skill errors."""


class SkillValidationError(SkillError):
    """Raised when a skill request or result fails contract validation."""


class SkillExecutionError(SkillError):
    """Raised when a skill fails during execution."""


class BaseSkill(ABC):
    """
    Base contract for all executable Aion Business skills.

    Lifecycle:
    1. validate_request()
    2. run()
    3. validate_result()
    """

    @property
    @abstractmethod
    def skill_id(self) -> str:
        raise NotImplementedError

    @property
    def version(self) -> str:
        return "v1"

    def supports(self, request: SkillRunRequest) -> bool:
        return request.skill_id == self.skill_id

    def validate_request(self, request: SkillRunRequest) -> None:
        """
        Validate the inbound skill request before execution.
        Override in concrete skills for stricter checks.
        """
        if request.skill_id != self.skill_id:
            raise SkillValidationError(
                f"skill_id_mismatch: expected={self.skill_id} got={request.skill_id}"
            )

        if not request.agent_id:
            raise SkillValidationError("missing_agent_id")

        if not request.task_id:
            raise SkillValidationError("missing_task_id")

        if not isinstance(request.input_payload, dict):
            raise SkillValidationError("input_payload_must_be_object")

        if not isinstance(request.allowed_tools, list):
            raise SkillValidationError("allowed_tools_must_be_list")

        if not isinstance(request.allowed_containers, list):
            raise SkillValidationError("allowed_containers_must_be_list")

    @abstractmethod
    def run(self, request: SkillRunRequest) -> SkillRunResult:
        """
        Execute the skill.
        Must return a structured SkillRunResult.
        """
        raise NotImplementedError

    def validate_result(self, result: SkillRunResult) -> None:
        """
        Validate the structured result returned by the skill.
        """
        if result.skill_id != self.skill_id:
            raise SkillValidationError(
                f"result_skill_id_mismatch: expected={self.skill_id} got={result.skill_id}"
            )

        if not isinstance(result.ok, bool):
            raise SkillValidationError("result_ok_must_be_bool")

        if not isinstance(result.output_payload, dict):
            raise SkillValidationError("result_output_payload_must_be_object")

        if not isinstance(result.artifacts, list):
            raise SkillValidationError("result_artifacts_must_be_list")

        if not isinstance(result.warnings, list):
            raise SkillValidationError("result_warnings_must_be_list")

        if result.error_code is not None and not isinstance(result.error_code, str):
            raise SkillValidationError("result_error_code_must_be_string_or_null")

        if not isinstance(result.trace, dict):
            raise SkillValidationError("result_trace_must_be_object")

        if not isinstance(result.side_effects_applied, bool):
            raise SkillValidationError("result_side_effects_applied_must_be_bool")

    def build_error_result(
        self,
        *,
        error_code: str,
        message: str,
        trace: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> SkillRunResult:
        return SkillRunResult(
            ok=False,
            skill_id=self.skill_id,
            output_payload={"message": message},
            artifacts=[],
            warnings=warnings or [],
            error_code=error_code,
            trace=trace or {},
            side_effects_applied=False,
        )