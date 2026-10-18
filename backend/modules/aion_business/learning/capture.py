from __future__ import annotations

import secrets
from typing import List, Optional

from backend.modules.aion_business.contracts.tasks import LearningRecord, TaskRecord


class LearningCaptureService:
    """
    v1 learning capture for Aion Business.

    Converts task outcomes into advisory learning records.

    Current rules:
    - completed -> success
    - failed -> failure
    - escalated -> routing_hint
    - provider fallback detected -> routing_hint

    Important:
    - advisory only
    - no autonomous policy mutation
    """

    def capture_from_task(
        self,
        task: TaskRecord,
        *,
        business_area: str,
    ) -> List[LearningRecord]:
        records: List[LearningRecord] = []

        status = task.status

        if status == "completed":
            record = self.capture_success(task, business_area=business_area)
            if record:
                records.append(record)

        elif status == "failed":
            record = self.capture_failure(task, business_area=business_area)
            if record:
                records.append(record)

        elif status == "escalated":
            record = self.capture_escalation(task, business_area=business_area)
            if record:
                records.append(record)

        fallback_record = self.capture_provider_fallback(task, business_area=business_area)
        if fallback_record:
            records.append(fallback_record)

        return records

    def capture_success(
        self,
        task: TaskRecord,
        *,
        business_area: str,
    ) -> Optional[LearningRecord]:
        summary = self._success_summary(task)
        if not summary:
            return None

        return LearningRecord(
            id=self._new_id(),
            source_type="task",
            source_id=task.id,
            business_area=business_area,
            signal_type="success",
            summary=summary,
            confidence=0.8,
            writable_influence=False,
        )

    def capture_failure(
        self,
        task: TaskRecord,
        *,
        business_area: str,
    ) -> Optional[LearningRecord]:
        error_text = self._extract_error(task)
        summary = (
            f"Task failed for role {task.owned_by_role}: {task.objective}. "
            f"Error: {error_text or 'unknown_error'}"
        )

        return LearningRecord(
            id=self._new_id(),
            source_type="task",
            source_id=task.id,
            business_area=business_area,
            signal_type="failure",
            summary=summary,
            confidence=0.9,
            writable_influence=False,
        )

    def capture_escalation(
        self,
        task: TaskRecord,
        *,
        business_area: str,
    ) -> Optional[LearningRecord]:
        escalation = task.outputs.get("escalation", {})
        reason = escalation.get("reason", "unknown_escalation_reason")
        target = escalation.get("target", "unknown_target")

        summary = (
            f"Task required escalation for role {task.owned_by_role}: {task.objective}. "
            f"Reason: {reason}. Target: {target}."
        )

        return LearningRecord(
            id=self._new_id(),
            source_type="task",
            source_id=task.id,
            business_area=business_area,
            signal_type="routing_hint",
            summary=summary,
            confidence=0.85,
            writable_influence=False,
        )

    def capture_provider_fallback(
        self,
        task: TaskRecord,
        *,
        business_area: str,
    ) -> Optional[LearningRecord]:
        workflow = task.outputs.get("campaign_planning_workflow", {})
        if not isinstance(workflow, dict):
            return None

        outputs = workflow.get("outputs", {})
        if not isinstance(outputs, dict):
            return None

        draft_content = outputs.get("draft_content", {})
        if not isinstance(draft_content, dict):
            return None

        draft_payload = draft_content.get("output_payload", {})
        if not isinstance(draft_payload, dict):
            return None

        fallback_used = bool(draft_payload.get("fallback_used", False))
        if not fallback_used:
            return None

        provider = draft_payload.get("provider", "unknown_provider")
        model = draft_payload.get("model", "unknown_model")

        summary = (
            f"Provider fallback was used during task execution for {task.objective}. "
            f"Provider: {provider}. Model: {model}."
        )

        return LearningRecord(
            id=self._new_id(),
            source_type="task",
            source_id=task.id,
            business_area=business_area,
            signal_type="routing_hint",
            summary=summary,
            confidence=0.7,
            writable_influence=False,
        )

    @staticmethod
    def _new_id() -> str:
        return f"learn-{secrets.token_hex(6)}"

    @staticmethod
    def _extract_error(task: TaskRecord) -> Optional[str]:
        error = task.outputs.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()

        workflow = task.outputs.get("campaign_planning_workflow", {})
        if isinstance(workflow, dict):
            workflow_error = workflow.get("error")
            if isinstance(workflow_error, str) and workflow_error.strip():
                return workflow_error.strip()

        return None

    @staticmethod
    def _success_summary(task: TaskRecord) -> Optional[str]:
        workflow_id = task.outputs.get("workflow_id")
        workflow_status = task.outputs.get("workflow_status")

        if workflow_id and workflow_status:
            return (
                f"Task completed successfully for role {task.owned_by_role}: {task.objective}. "
                f"Workflow {workflow_id} finished with status {workflow_status}."
            )

        summary = task.outputs.get("summary")
        if isinstance(summary, str) and summary.strip():
            return f"Task completed successfully for role {task.owned_by_role}: {summary.strip()}"

        return f"Task completed successfully for role {task.owned_by_role}: {task.objective}."