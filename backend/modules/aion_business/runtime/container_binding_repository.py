from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_business.contracts.containers import ContainerBindingSpec
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class ContainerBindingRepository:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else AIONBusinessPaths.CONTAINER_BINDINGS
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _workspace_dir(self, workspace_id: str) -> Path:
        path = self.base_dir / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _binding_path(self, workspace_id: str, binding_id: str) -> Path:
        return self._workspace_dir(workspace_id) / f"{binding_id}.json"

    def save(self, binding: ContainerBindingSpec) -> str:
        path = self._binding_path(binding.workspace_id, binding.id)
        path.write_text(
            json.dumps(binding.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return str(path)

    def load(self, workspace_id: str, binding_id: str) -> ContainerBindingSpec:
        path = self._binding_path(workspace_id, binding_id)
        if not path.exists():
            raise FileNotFoundError(f"Container binding not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ContainerBindingSpec(**data)

    def load_optional(
        self,
        workspace_id: str,
        binding_id: str,
    ) -> Optional[ContainerBindingSpec]:
        path = self._binding_path(workspace_id, binding_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ContainerBindingSpec(**data)

    def get(self, binding_id: str) -> ContainerBindingSpec:
        """
        Resolve a binding globally across workspace binding directories.

        v1 assumption:
        binding ids are unique across the Aion Business runtime.
        """
        for workspace_id in self.list_workspace_ids():
            path = self.base_dir / workspace_id / f"{binding_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return ContainerBindingSpec(**data)
        raise FileNotFoundError(f"Container binding not found by id: {binding_id}")

    def exists(self, workspace_id: str, binding_id: str) -> bool:
        return self._binding_path(workspace_id, binding_id).exists()

    def list_workspace_ids(self) -> List[str]:
        if not self.base_dir.exists():
            return []
        return sorted(p.name for p in self.base_dir.iterdir() if p.is_dir())

    def list_ids(self, workspace_id: str) -> List[str]:
        workspace_dir = self._workspace_dir(workspace_id)
        return sorted(p.stem for p in workspace_dir.glob("*.json"))

    def list_bindings(self, workspace_id: str) -> List[ContainerBindingSpec]:
        return [
            self.load(workspace_id, binding_id)
            for binding_id in self.list_ids(workspace_id)
        ]

    def delete(self, workspace_id: str, binding_id: str) -> bool:
        path = self._binding_path(workspace_id, binding_id)
        if not path.exists():
            return False
        path.unlink()
        return True