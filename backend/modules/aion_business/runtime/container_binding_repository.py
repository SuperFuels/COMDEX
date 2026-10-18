from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_business.contracts.containers import ContainerBindingSpec
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.department_operational_store import (
    BusinessOperationsRecordRepository,
    DepartmentOperationalStore,
)


class ContainerBindingRepository:
    def __init__(
        self, base_dir: str | Path | None = None, *,
        operational_store: DepartmentOperationalStore | None = None,
    ) -> None:
        self.records = BusinessOperationsRecordRepository(
            "container_bindings", operational_store=operational_store,
        )
        self.explicit_legacy_root = base_dir is not None
        self.base_dir = Path(base_dir) if base_dir else AIONBusinessPaths.CONTAINER_BINDINGS
        if self.explicit_legacy_root or not self.records.enabled:
            self.base_dir.mkdir(parents=True, exist_ok=True)

    def _workspace_dir(self, workspace_id: str) -> Path:
        path = self.base_dir / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _binding_path(self, workspace_id: str, binding_id: str) -> Path:
        return self._workspace_dir(workspace_id) / f"{binding_id}.json"

    def save(self, binding: ContainerBindingSpec) -> str:
        if self.records.enabled and not self.explicit_legacy_root:
            self.records.put(
                binding.workspace_id, binding.id, binding.model_dump(mode="json"),
                actor_id="container-binding-repository",
            )
            return f"vault://departments.operational_records/{binding.workspace_id}/business_operations/container_bindings/{binding.id}"
        path = self._binding_path(binding.workspace_id, binding.id)
        path.write_text(
            json.dumps(binding.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return str(path)

    def load(self, workspace_id: str, binding_id: str) -> ContainerBindingSpec:
        if self.records.enabled and not self.explicit_legacy_root:
            record = self.records.get_optional(workspace_id, binding_id)
            if record is None:
                raise FileNotFoundError(f"Container binding not found: {workspace_id}/{binding_id}")
            return ContainerBindingSpec(**record["payload"])
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
        if self.records.enabled and not self.explicit_legacy_root:
            record = self.records.get_optional(workspace_id, binding_id)
            return ContainerBindingSpec(**record["payload"]) if record else None
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
        if self.records.enabled and not self.explicit_legacy_root:
            matches = [
                row for row in self.records.list_all()
                if str((row.get("payload") or {}).get("id") or "") == binding_id
            ]
            if len(matches) == 1:
                return ContainerBindingSpec(**matches[0]["payload"])
            if len(matches) > 1:
                raise RuntimeError(f"Container binding id is not unique: {binding_id}")
            raise FileNotFoundError(f"Container binding not found by id: {binding_id}")
        for workspace_id in self.list_workspace_ids():
            path = self.base_dir / workspace_id / f"{binding_id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return ContainerBindingSpec(**data)
        raise FileNotFoundError(f"Container binding not found by id: {binding_id}")

    def exists(self, workspace_id: str, binding_id: str) -> bool:
        if self.records.enabled and not self.explicit_legacy_root:
            return self.records.get_optional(workspace_id, binding_id) is not None
        return self._binding_path(workspace_id, binding_id).exists()

    def list_workspace_ids(self) -> List[str]:
        if self.records.enabled and not self.explicit_legacy_root:
            return sorted({str(row["workspace_id"]) for row in self.records.list_all()})
        if not self.base_dir.exists():
            return []
        return sorted(p.name for p in self.base_dir.iterdir() if p.is_dir())

    def list_ids(self, workspace_id: str) -> List[str]:
        if self.records.enabled and not self.explicit_legacy_root:
            return sorted(
                str((row.get("payload") or {}).get("id") or "")
                for row in self.records.list_workspace(workspace_id)
            )
        workspace_dir = self._workspace_dir(workspace_id)
        return sorted(p.stem for p in workspace_dir.glob("*.json"))

    def list_bindings(self, workspace_id: str) -> List[ContainerBindingSpec]:
        return [
            self.load(workspace_id, binding_id)
            for binding_id in self.list_ids(workspace_id)
        ]

    def delete(self, workspace_id: str, binding_id: str) -> bool:
        if self.records.enabled and not self.explicit_legacy_root:
            return self.records.delete(
                workspace_id, binding_id, actor_id="container-binding-repository",
            )
        path = self._binding_path(workspace_id, binding_id)
        if not path.exists():
            return False
        path.unlink()
        return True
