from __future__ import annotations

from typing import List, Optional

from backend.modules.aion_business.contracts.tasks import LearningRecord, TaskRecord
from backend.modules.aion_business.learning.capture import LearningCaptureService
from backend.modules.aion_business.runtime.learning_repository import LearningRepository


class LearningService:
    """
    Small orchestration layer for learning capture + persistence.

    Responsibilities:
    - capture learning records from task outcomes
    - persist those records
    - expose simple query helpers for workspace learning
    """

    def __init__(
        self,
        *,
        capture_service: Optional[LearningCaptureService] = None,
        repository: Optional[LearningRepository] = None,
    ):
        self.capture_service = capture_service or LearningCaptureService()
        self.repository = repository or LearningRepository()

    def capture_and_save_from_task(
        self,
        *,
        workspace_id: str,
        task: TaskRecord,
        business_area: str,
    ) -> List[LearningRecord]:
        records = self.capture_service.capture_from_task(
            task,
            business_area=business_area,
        )
        for record in records:
            self.repository.save(record, workspace_id)
        return records

    def save_record(
        self,
        *,
        workspace_id: str,
        record: LearningRecord,
    ):
        return self.repository.save(record, workspace_id)

    def load_record(
        self,
        *,
        workspace_id: str,
        record_id: str,
    ) -> LearningRecord:
        return self.repository.load(workspace_id, record_id)

    def list_workspace_learning(
        self,
        *,
        workspace_id: str,
    ) -> List[LearningRecord]:
        return self.repository.list_all(workspace_id)

    def list_by_signal_type(
        self,
        *,
        workspace_id: str,
        signal_type: str,
    ) -> List[LearningRecord]:
        return self.repository.list_by_signal_type(workspace_id, signal_type)

    def list_by_source_type(
        self,
        *,
        workspace_id: str,
        source_type: str,
    ) -> List[LearningRecord]:
        return self.repository.list_by_source_type(workspace_id, source_type)

    def list_by_business_area(
        self,
        *,
        workspace_id: str,
        business_area: str,
    ) -> List[LearningRecord]:
        return self.repository.list_by_business_area(workspace_id, business_area)