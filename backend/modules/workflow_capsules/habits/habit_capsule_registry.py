from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import time

from backend.modules.workflow_capsules.habits.habit_capsule_repository import (
    HabitCapsuleRepository,
)
from backend.modules.workflow_capsules.habits.habit_capsule_schema import HabitCapsule


REGISTRY_SCHEMA_VERSION = "aion.habit_capsule_registry.v1"


def _now() -> float:
    return time.time()


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


@dataclass
class HabitCapsuleRegistryEntry:
    habit_key: str
    source_workflow_key: str
    habit_path: str

    display_name: str = ""
    trigger_tags: List[str] = field(default_factory=list)
    checksum: Optional[str] = None
    schema_version: str = REGISTRY_SCHEMA_VERSION
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_habit(cls, habit: HabitCapsule, *, habit_path: str) -> "HabitCapsuleRegistryEntry":
        return cls(
            habit_key=habit.habit_key,
            source_workflow_key=habit.source_workflow_key,
            habit_path=str(habit_path),
            display_name=habit.display_name,
            trigger_tags=list(habit.trigger_tags or []),
            checksum=(habit.meta or {}).get("checksum") or habit.checksum(),
        )


@dataclass
class HabitCapsuleMatch:
    habit_key: str
    source_workflow_key: str
    reason: str
    score: float
    entry: HabitCapsuleRegistryEntry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "habit_key": self.habit_key,
            "source_workflow_key": self.source_workflow_key,
            "reason": self.reason,
            "score": self.score,
            "entry": self.entry.to_dict(),
        }


class HabitCapsuleRegistry:
    """
    Resolver over promoted Habit Capsules.

    Safety invariant:
      Habit resolution is advisory. It returns source_workflow_key.
      Execution MUST still go through the normal WorkflowCapsuleRunner path.
    """

    def __init__(
        self,
        *,
        repository: Optional[HabitCapsuleRepository] = None,
        registry_path: Path | str = ".runtime/workflow_capsules/habits/habit_capsule_registry.json",
    ) -> None:
        self.repository = repository or HabitCapsuleRepository()
        self.registry_path = Path(registry_path)
        self.entries: Dict[str, HabitCapsuleRegistryEntry] = {}

    def build_from_repository(self) -> Dict[str, Any]:
        discovered: Dict[str, HabitCapsuleRegistryEntry] = {}

        for item in self.repository.list_habits():
            habit = item.get("habit")
            path = item.get("path")
            if isinstance(habit, HabitCapsule) and path:
                discovered[habit.habit_key] = HabitCapsuleRegistryEntry.from_habit(
                    habit,
                    habit_path=str(path),
                )

        self.entries = dict(sorted(discovered.items(), key=lambda kv: kv[0]))

        return {
            "ok": True,
            "count": len(self.entries),
            "discovered": len(discovered),
        }

    def save(self) -> Dict[str, Any]:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "updated_at": _now(),
            "count": len(self.entries),
            "entries": {
                key: entry.to_dict()
                for key, entry in sorted(self.entries.items(), key=lambda kv: kv[0])
            },
        }
        self.registry_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "ok": True,
            "path": str(self.registry_path),
            "count": len(self.entries),
        }

    def rebuild_and_save(self) -> Dict[str, Any]:
        build = self.build_from_repository()
        saved = self.save()
        return {
            "ok": bool(build.get("ok")) and bool(saved.get("ok")),
            "build": build,
            "saved": saved,
        }

    def load(self) -> Dict[str, Any]:
        if not self.registry_path.exists():
            return {"ok": False, "error": "registry_not_found", "path": str(self.registry_path)}

        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        raw_entries = dict(data.get("entries") or {})
        self.entries = {
            key: HabitCapsuleRegistryEntry(**entry)
            for key, entry in raw_entries.items()
            if isinstance(entry, dict)
        }
        return {
            "ok": True,
            "path": str(self.registry_path),
            "count": len(self.entries),
        }

    def find(self, query: str) -> List[HabitCapsuleMatch]:
        q = _norm(query)
        ql = _norm_lower(q)
        if not q:
            return []

        matches: List[HabitCapsuleMatch] = []

        for key, entry in self.entries.items():
            if q == entry.habit_key:
                matches.append(HabitCapsuleMatch(
                    habit_key=entry.habit_key,
                    source_workflow_key=entry.source_workflow_key,
                    reason="exact_habit_key",
                    score=1.0,
                    entry=entry,
                ))
                continue

            if q == entry.source_workflow_key:
                matches.append(HabitCapsuleMatch(
                    habit_key=entry.habit_key,
                    source_workflow_key=entry.source_workflow_key,
                    reason="exact_source_workflow_key",
                    score=0.96,
                    entry=entry,
                ))
                continue

            if ql == _norm_lower(entry.display_name):
                matches.append(HabitCapsuleMatch(
                    habit_key=entry.habit_key,
                    source_workflow_key=entry.source_workflow_key,
                    reason="display_name",
                    score=0.90,
                    entry=entry,
                ))
                continue

            if ql in [_norm_lower(t) for t in entry.trigger_tags]:
                matches.append(HabitCapsuleMatch(
                    habit_key=entry.habit_key,
                    source_workflow_key=entry.source_workflow_key,
                    reason="trigger_tag",
                    score=0.76,
                    entry=entry,
                ))
                continue

            haystack = " ".join([
                entry.habit_key,
                entry.source_workflow_key,
                entry.display_name,
                " ".join(entry.trigger_tags or []),
            ]).lower()

            if ql in haystack:
                matches.append(HabitCapsuleMatch(
                    habit_key=entry.habit_key,
                    source_workflow_key=entry.source_workflow_key,
                    reason="semantic_text",
                    score=0.62,
                    entry=entry,
                ))

        return sorted(matches, key=lambda m: m.score, reverse=True)

    def require(self, query: str) -> HabitCapsule:
        matches = self.find(query)
        if not matches:
            raise FileNotFoundError(f"Habit capsule not found: {query}")
        return self.repository.require(matches[0].habit_key)

    def resolve_source_workflow_key(self, query: str) -> str:
        matches = self.find(query)
        if not matches:
            raise FileNotFoundError(f"Habit capsule not found: {query}")
        return matches[0].source_workflow_key
