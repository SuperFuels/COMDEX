from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from backend.modules.aion_business.contracts.tasks import LearningRecord
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class LearningRepository:
    """
    File-backed repository for LearningRecord objects.

    Layout:
    .runtime/AION_BUSINESS/learning/<workspace_id>/<learning_id>.json
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is not None:
            raise ValueError(
                "LearningRepository currently uses the global AIONBusinessPaths "
                "layout; base_dir override is not supported in this version."
            )

    def _learning_path(self, workspace_id: str, record_id: str) -> Path:
        return AIONBusinessPaths.learning_file(workspace_id, record_id)

    def save(self, record: LearningRecord, workspace_id: str) -> Path:
        path = self._learning_path(workspace_id, record.id)
        path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, workspace_id: str, record_id: str) -> LearningRecord:
        path = self._learning_path(workspace_id, record_id)
        if not path.exists():
            raise FileNotFoundError(f"Learning record not found: {workspace_id}/{record_id}")

        data = json.loads(path.read_text(encoding="utf-8"))
        return LearningRecord(**data)

    def list_ids(self, workspace_id: str) -> List[str]:
        path = AIONBusinessPaths.learning_dir(workspace_id)
        return sorted(p.stem for p in path.glob("*.json"))

    def list_all(self, workspace_id: str) -> List[LearningRecord]:
        return [self.load(workspace_id, record_id) for record_id in self.list_ids(workspace_id)]

    def list_by_signal_type(
        self,
        workspace_id: str,
        signal_type: str,
    ) -> List[LearningRecord]:
        return [
            record
            for record in self.list_all(workspace_id)
            if record.signal_type == signal_type
        ]

    def list_by_source_type(
        self,
        workspace_id: str,
        source_type: str,
    ) -> List[LearningRecord]:
        return [
            record
            for record in self.list_all(workspace_id)
            if record.source_type == source_type
        ]

    def list_by_business_area(
        self,
        workspace_id: str,
        business_area: str,
    ) -> List[LearningRecord]:
        return [
            record
            for record in self.list_all(workspace_id)
            if record.business_area == business_area
        ]