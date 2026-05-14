from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_agents.contracts.trigger_definition import TriggerDefinition


class TriggerDefinitionRepository:
    """
    File-backed repository for trigger definitions.

    Canonical layout:
      <base_dir>/<workspace_id>/aion_agents/trigger_definitions/<trigger_id>.json
    """

    def __init__(self, base_dir: str | Path = ".runtime") -> None:
        self.base_dir = Path(base_dir)

    def _workspace_dir(self, workspace_id: str) -> Path:
        return self.base_dir / workspace_id / "aion_agents" / "trigger_definitions"

    def _path(self, workspace_id: str, trigger_id: str) -> Path:
        return self._workspace_dir(workspace_id) / f"{trigger_id}.json"

    def save(self, model: TriggerDefinition) -> TriggerDefinition:
        trigger_id = getattr(model, "trigger_id", None) or getattr(model, "id", None)
        if not trigger_id:
            raise ValueError("TriggerDefinition missing trigger_id/id")

        path = self._path(model.workspace_id, str(trigger_id))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return model

    def load(self, workspace_id: str, trigger_id: str) -> TriggerDefinition:
        path = self._path(workspace_id, trigger_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Trigger definition not found: workspace_id={workspace_id} trigger_id={trigger_id}"
            )
        return TriggerDefinition(**json.loads(path.read_text(encoding="utf-8")))

    def get(self, workspace_id: str, trigger_id: str) -> Optional[TriggerDefinition]:
        try:
            return self.load(workspace_id, trigger_id)
        except FileNotFoundError:
            return None

    def load_optional(self, workspace_id: str, trigger_id: str) -> Optional[TriggerDefinition]:
        return self.get(workspace_id, trigger_id)

    def find_one(self, workspace_id: str, trigger_id: str) -> Optional[TriggerDefinition]:
        return self.get(workspace_id, trigger_id)

    def exists(self, workspace_id: str, trigger_id: str) -> bool:
        return self._path(workspace_id, trigger_id).exists()

    def delete(self, workspace_id: str, trigger_id: str) -> bool:
        path = self._path(workspace_id, trigger_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_all(self, workspace_id: str) -> List[TriggerDefinition]:
        directory = self._workspace_dir(workspace_id)
        if not directory.exists():
            return []

        out: List[TriggerDefinition] = []
        for path in sorted(directory.glob("*.json")):
            try:
                out.append(
                    TriggerDefinition(**json.loads(path.read_text(encoding="utf-8")))
                )
            except Exception:
                continue
        return out