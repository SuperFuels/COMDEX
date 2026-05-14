from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from backend.modules.workflow_capsules.habits.habit_capsule_schema import HabitCapsule


DEFAULT_HABIT_DIR = Path(".runtime/workflow_capsules/habits")


class HabitCapsuleRepository:
    """
    Runtime repository for promoted Habit Capsules.

    Important:
      - Habit Capsules are runtime reinforcement artifacts.
      - They do not replace source Workflow Capsules.
      - They resolve back to source_workflow_key for normal policy/vault/approval execution.
    """

    def __init__(self, habit_dir: Path | str = DEFAULT_HABIT_DIR) -> None:
        self.habit_dir = Path(habit_dir)

    def path_for_key(self, habit_key: str) -> Path:
        safe = str(habit_key or "habit.unknown.v1").replace(":", "_").replace("/", "_")
        return self.habit_dir / f"{safe}.json"

    def save(self, habit: HabitCapsule) -> Dict[str, Any]:
        path = self.path_for_key(habit.habit_key)
        habit.save(path)
        return {
            "ok": True,
            "habit_key": habit.habit_key,
            "source_workflow_key": habit.source_workflow_key,
            "path": str(path),
            "checksum": habit.meta.get("checksum"),
        }

    def load(self, habit_key: str) -> Optional[HabitCapsule]:
        path = self.path_for_key(habit_key)
        if not path.exists():
            return None
        return HabitCapsule.load(path)

    def require(self, habit_key: str) -> HabitCapsule:
        habit = self.load(habit_key)
        if habit is None:
            raise FileNotFoundError(f"Habit capsule not found: {habit_key}")
        return habit

    def list_habits(self) -> List[Dict[str, Any]]:
        if not self.habit_dir.exists():
            return []

        out: List[Dict[str, Any]] = []
        for path in sorted(self.habit_dir.glob("habit_*.json")):
            try:
                habit = HabitCapsule.load(path)
                out.append({
                    "habit": habit,
                    "path": str(path),
                })
            except Exception:
                continue
        return out
