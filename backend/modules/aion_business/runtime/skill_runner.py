from __future__ import annotations

from typing import Dict, Iterable, Optional

from backend.modules.aion_business.contracts.skills import SkillRunRequest, SkillRunResult
from backend.modules.aion_business.skills.base import (
    BaseSkill,
    SkillExecutionError,
    SkillValidationError,
)


class SkillNotRegisteredError(ValueError):
    """Raised when a requested skill is not registered in the runner."""


class SkillRunner:
    """
    Executes skills against the shared BaseSkill contract.

    Flow:
    1. resolve registered skill
    2. validate request
    3. execute skill
    4. validate result
    5. return structured SkillRunResult
    """

    def __init__(self, skills: Optional[Iterable[BaseSkill]] = None):
        self._skills: Dict[str, BaseSkill] = {}
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.skill_id] = skill

    def unregister(self, skill_id: str) -> None:
        self._skills.pop(skill_id, None)

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def get_skill(self, skill_id: str) -> BaseSkill:
        skill = self._skills.get(skill_id)
        if skill is None:
            raise SkillNotRegisteredError(f"skill_not_registered:{skill_id}")
        return skill

    def list_skill_ids(self) -> list[str]:
        return sorted(self._skills.keys())

    def run(self, request: SkillRunRequest) -> SkillRunResult:
        skill = self.get_skill(request.skill_id)

        try:
            skill.validate_request(request)
            result = skill.run(request)
            skill.validate_result(result)
            return result

        except SkillValidationError as exc:
            return skill.build_error_result(
                error_code="skill_validation_error",
                message=str(exc),
                trace={
                    "skill_id": skill.skill_id,
                    "stage": "validation",
                    "agent_id": request.agent_id,
                    "task_id": request.task_id,
                },
            )

        except SkillExecutionError as exc:
            return skill.build_error_result(
                error_code="skill_execution_error",
                message=str(exc),
                trace={
                    "skill_id": skill.skill_id,
                    "stage": "execution",
                    "agent_id": request.agent_id,
                    "task_id": request.task_id,
                },
            )

        except Exception as exc:
            return skill.build_error_result(
                error_code="skill_unhandled_error",
                message=f"{type(exc).__name__}: {exc}",
                trace={
                    "skill_id": skill.skill_id,
                    "stage": "unhandled_exception",
                    "agent_id": request.agent_id,
                    "task_id": request.task_id,
                },
            )