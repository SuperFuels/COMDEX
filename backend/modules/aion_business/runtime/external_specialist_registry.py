from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_business.contracts.external_specialists import (
    ExternalSpecialistSelection,
    ExternalSpecialistSpec,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class ExternalSpecialistRegistry:
    def __init__(self) -> None:
        AIONBusinessPaths.ensure_base_dirs()

    def _registry_dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.ROOT / "external_specialists" / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _registry_file(self, workspace_id: str, specialist_id: str) -> Path:
        return self._registry_dir(workspace_id) / f"{specialist_id}.json"

    def save(self, spec: ExternalSpecialistSpec) -> Path:
        path = self._registry_file(spec.workspace_id, spec.id)
        path.write_text(
            json.dumps(spec.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, workspace_id: str, specialist_id: str) -> ExternalSpecialistSpec:
        path = self._registry_file(workspace_id, specialist_id)
        if not path.exists():
            raise FileNotFoundError(
                f"External specialist not found: {workspace_id}/{specialist_id}"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        return ExternalSpecialistSpec(**data)

    def list_ids(self, workspace_id: str) -> List[str]:
        return sorted(p.stem for p in self._registry_dir(workspace_id).glob("*.json"))

    def list_all(self, workspace_id: str) -> List[ExternalSpecialistSpec]:
        return [self.load(workspace_id, specialist_id) for specialist_id in self.list_ids(workspace_id)]

    def list_enabled(self, workspace_id: str) -> List[ExternalSpecialistSpec]:
        return [spec for spec in self.list_all(workspace_id) if spec.enabled]

    def list_by_capability(self, workspace_id: str, capability: str) -> List[ExternalSpecialistSpec]:
        matches = [
            spec
            for spec in self.list_enabled(workspace_id)
            if capability in spec.capabilities
        ]
        return sorted(matches, key=lambda spec: spec.priority)

    def resolve_for_capability(
        self,
        *,
        workspace_id: str,
        capability: str,
    ) -> ExternalSpecialistSelection:
        matches = self.list_by_capability(workspace_id, capability)

        if not matches:
            return ExternalSpecialistSelection(
                workspace_id=workspace_id,
                capability=capability,
                selected_specialist_id=None,
                fallback_specialist_ids=[],
                reason="no_enabled_specialist_for_capability",
            )

        primary = matches[0]
        fallbacks = [spec.id for spec in matches[1:]]

        return ExternalSpecialistSelection(
            workspace_id=workspace_id,
            capability=capability,
            selected_specialist_id=primary.id,
            fallback_specialist_ids=fallbacks,
            reason="selected_by_priority",
        )