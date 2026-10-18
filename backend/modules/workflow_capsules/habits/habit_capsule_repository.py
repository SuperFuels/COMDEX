from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os

from backend.modules.workflow_capsules.habits.habit_capsule_schema import HabitCapsule
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_agents.runtime.vault_repository_backend import (
    AgentVaultRepositoryBackend,
    configured_agent_domain_store,
)


DEFAULT_HABIT_DIR = Path(".runtime/workflow_capsules/habits")


class HabitCapsuleRepository:
    """
    Runtime repository for promoted Habit Capsules.

    Important:
      - Habit Capsules are runtime reinforcement artifacts.
      - They do not replace source Workflow Capsules.
      - They resolve back to source_workflow_key for normal policy/vault/approval execution.
    """

    def __init__(
        self,
        habit_dir: Path | str | None = None,
        *,
        domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
    ) -> None:
        self.habit_dir = Path(habit_dir or DEFAULT_HABIT_DIR)
        store = domain_store or (
            configured_agent_domain_store() if habit_dir is None else None
        )
        self.vault = (
            AgentVaultRepositoryBackend(
                store,
                kind="workflow_capsule_habits",
            )
            if store
            else None
        )
        self.workspace_id = str(
            workspace_id
            or os.environ.get("TESSARIS_BUSINESS_STABLE_ID")
            or ""
        ).strip()
        if self.vault is not None and not self.workspace_id:
            raise ValueError("workflow_capsule_habit_workspace_id_required")

    @staticmethod
    def _item_id(habit_key: str) -> str:
        return str(habit_key or "habit.unknown.v1").replace("/", "_")

    def _vault_path(self, habit_key: str) -> str:
        return (
            "vault://train_agent.automations/workflow_capsule_habits/"
            + self._item_id(habit_key)
        )

    def path_for_key(self, habit_key: str) -> Path:
        safe = str(habit_key or "habit.unknown.v1").replace(":", "_").replace("/", "_")
        return self.habit_dir / f"{safe}.json"

    def save(self, habit: HabitCapsule) -> Dict[str, Any]:
        habit.finalize()
        if self.vault is not None:
            self.vault.put(
                workspace_id=self.workspace_id,
                item_id=self._item_id(habit.habit_key),
                payload=habit.to_dict(),
            )
            return {
                "ok": True,
                "habit_key": habit.habit_key,
                "source_workflow_key": habit.source_workflow_key,
                "path": self._vault_path(habit.habit_key),
                "checksum": habit.meta.get("checksum"),
            }
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
        if self.vault is not None:
            payload = self.vault.get(
                workspace_id=self.workspace_id,
                item_id=self._item_id(habit_key),
            )
            return HabitCapsule.from_dict(payload) if payload is not None else None
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
        if self.vault is not None:
            out: List[Dict[str, Any]] = []
            for payload in self.vault.list(workspace_id=self.workspace_id):
                try:
                    habit = HabitCapsule.from_dict(payload)
                    out.append({
                        "habit": habit,
                        "path": self._vault_path(habit.habit_key),
                    })
                except Exception:
                    continue
            return sorted(out, key=lambda item: item["habit"].habit_key)
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
