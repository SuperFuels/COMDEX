from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class TaskRecordRepository:
    def __init__(self, base_dir: Optional[str | Path] = None):
        if base_dir is not None:
            raise ValueError(
                "TaskRecordRepository currently uses the global AIONBusinessPaths "
                "layout; base_dir override is not supported in this version."
            )

    def _task_path(self, workspace_id: str, task_id: str) -> Path:
        return AIONBusinessPaths.task_file(workspace_id, task_id)

    def save(self, task: TaskRecord) -> str:
        path = self._task_path(task.workspace_id, task.id)
        path.write_text(
            json.dumps(task.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return str(path)

    def load(self, workspace_id: str, task_id: str) -> TaskRecord:
        path = self._task_path(workspace_id, task_id)
        if not path.exists():
            raise FileNotFoundError(f"Task not found: {workspace_id}/{task_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return TaskRecord(**data)

    def list_ids(self, workspace_id: str | None = None) -> List[str]:
        if workspace_id:
            ws_dir = AIONBusinessPaths.task_dir(workspace_id)
            return sorted(p.stem for p in ws_dir.glob("*.json"))

        root = AIONBusinessPaths.TASKS
        if not root.exists():
            return []

        ids: List[str] = []
        for ws_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            ids.extend(sorted(p.stem for p in ws_dir.glob("*.json")))
        return ids

    def list_for_workspace(self, workspace_id: str) -> List[TaskRecord]:
        ws_dir = AIONBusinessPaths.task_dir(workspace_id)
        out: List[TaskRecord] = []
        for path in sorted(ws_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append(TaskRecord(**data))
        return out

    def list_for_role(self, workspace_id: str, role_id: str) -> List[TaskRecord]:
        return [
            task
            for task in self.list_for_workspace(workspace_id)
            if task.owned_by_role == role_id
        ]