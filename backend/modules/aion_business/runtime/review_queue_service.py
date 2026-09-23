from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.runtime.task_record_repository import TaskRecordRepository


class ReviewQueueService:
    """
    Central reusable review queue builder.

    Responsibilities:
    - load recent escalated tasks
    - build escalation snapshot
    - group queue by escalation target
    - group queue by owning role
    - return one reusable queue snapshot payload
    """

    def __init__(
        self,
        *,
        task_repository: Optional[TaskRecordRepository] = None,
    ):
        self.task_repository = task_repository or TaskRecordRepository()

    def build_queue_snapshot(
        self,
        *,
        workspace_id: str,
        days_back: int = 30,
    ) -> Dict:
        escalated = self._load_recent_escalated_tasks(
            workspace_id=workspace_id,
            days_back=days_back,
        )

        escalation_snapshot = {
            "count": len(escalated),
            "task_ids": [task.id for task in escalated],
            "tasks_preview": [self._task_preview(task) for task in escalated[:20]],
        }

        target_groups = self._group_by_target(escalated)
        role_groups = self._group_by_role(escalated)

        return {
            "workspace_id": workspace_id,
            "days_back": days_back,
            "escalation_snapshot": escalation_snapshot,
            "target_groups": target_groups,
            "role_groups": role_groups,
        }

    def _load_recent_escalated_tasks(
        self,
        *,
        workspace_id: str,
        days_back: int,
    ) -> List[TaskRecord]:
        tasks = self.task_repository.list_for_workspace(workspace_id)
        return [
            task
            for task in tasks
            if task.status == "escalated" and self._is_recent_task(task, days_back=days_back)
        ]

    def _group_by_target(self, tasks: List[TaskRecord]) -> Dict:
        grouped: Dict[str, List[TaskRecord]] = {}

        for task in tasks:
            escalation = task.outputs.get("escalation", {})
            target = escalation.get("target") or "unassigned_review_queue"
            grouped.setdefault(str(target), []).append(task)

        return {
            "count": len(grouped),
            "groups": {
                target: {
                    "count": len(group_tasks),
                    "task_ids": [t.id for t in group_tasks],
                    "preview": [self._task_preview(t) for t in group_tasks[:5]],
                }
                for target, group_tasks in grouped.items()
            },
        }

    def _group_by_role(self, tasks: List[TaskRecord]) -> Dict:
        grouped: Dict[str, List[TaskRecord]] = {}

        for task in tasks:
            owner = task.owned_by_role or "unassigned_role"
            grouped.setdefault(str(owner), []).append(task)

        return {
            "count": len(grouped),
            "groups": {
                owner: {
                    "count": len(group_tasks),
                    "task_ids": [t.id for t in group_tasks],
                    "preview": [self._task_preview(t) for t in group_tasks[:5]],
                }
                for owner, group_tasks in grouped.items()
            },
        }

    @staticmethod
    def _task_preview(task: TaskRecord) -> Dict:
        escalation = task.outputs.get("escalation", {})
        return {
            "id": task.id,
            "owned_by_role": task.owned_by_role,
            "objective": task.objective,
            "status": task.status,
            "escalation_reason": escalation.get("reason"),
            "escalation_target": escalation.get("target"),
            "updated_at": task.updated_at,
        }

    @staticmethod
    def _is_recent_task(task: TaskRecord, *, days_back: int) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        candidate = task.updated_at or task.completed_at or task.created_at

        if not candidate:
            return True

        try:
            dt = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except Exception:
            return True

        return dt >= cutoff