from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from backend.modules.aion_business.skills.base import BaseSkill


class SkillRegistry:
    """
    In-memory registry for Aion Business skills.

    This is intentionally simple for v1:
    - register skill instances
    - resolve by skill_id
    - list available skills
    - provide skills to the SkillRunner
    """

    def __init__(self, skills: Optional[Iterable[BaseSkill]] = None):
        self._skills: Dict[str, BaseSkill] = {}
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.skill_id] = skill

    def register_many(self, skills: Iterable[BaseSkill]) -> None:
        for skill in skills:
            self.register(skill)

    def unregister(self, skill_id: str) -> None:
        self._skills.pop(skill_id, None)

    def clear(self) -> None:
        self._skills.clear()

    def has(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def get(self, skill_id: str) -> BaseSkill:
        skill = self._skills.get(skill_id)
        if skill is None:
            raise KeyError(f"unknown_skill:{skill_id}")
        return skill

    def list_ids(self) -> List[str]:
        return sorted(self._skills.keys())

    def list_skills(self) -> List[BaseSkill]:
        return [self._skills[skill_id] for skill_id in self.list_ids()]

    def as_dict(self) -> Dict[str, BaseSkill]:
        return dict(self._skills)