from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import List, Optional

from backend.modules.aion_agents.contracts.trigger_definition import (
    TriggerDefinition,
    TriggerState,
    TriggerType,
    utc_now_iso,
)
from backend.modules.aion_agents.runtime.trigger_definition_repository import (
    TriggerDefinitionRepository,
)


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None


class TriggerService:
    def __init__(
        self,
        repository: Optional[TriggerDefinitionRepository] = None,
    ) -> None:
        self.repository = repository or TriggerDefinitionRepository()

    def list_triggers(self, workspace_id: str) -> List[TriggerDefinition]:
        return self.repository.list_all(workspace_id)

    def save_trigger(self, model: TriggerDefinition) -> TriggerDefinition:
        model.updated_at = utc_now_iso()
        return self.repository.save(model)

    def compute_next_run_at(
        self,
        trigger: TriggerDefinition,
        *,
        now: Optional[datetime] = None,
    ) -> Optional[str]:
        if trigger.trigger_type != TriggerType.SCHEDULE:
            return None
        if not trigger.cadence_minutes or trigger.cadence_minutes <= 0:
            return None

        now = now or datetime.now(UTC)
        base = parse_iso_datetime(trigger.next_run_at) or parse_iso_datetime(trigger.last_run_at)

        if base is None:
            return (now + timedelta(minutes=trigger.cadence_minutes)).replace(
                microsecond=0
            ).isoformat()

        next_dt = base
        while next_dt <= now:
            next_dt = next_dt + timedelta(minutes=trigger.cadence_minutes)

        return next_dt.replace(microsecond=0).isoformat()

    def should_skip_for_cooldown(
        self,
        trigger: TriggerDefinition,
        *,
        now: Optional[datetime] = None,
    ) -> bool:
        if trigger.cooldown_seconds <= 0:
            return False

        now = now or datetime.now(UTC)
        last_attempted = parse_iso_datetime(trigger.last_attempted_at)
        if last_attempted is None:
            return False

        return now < (last_attempted + timedelta(seconds=trigger.cooldown_seconds))

    def should_skip_for_dedupe(
        self,
        trigger: TriggerDefinition,
        *,
        dedupe_key: Optional[str] = None,
    ) -> bool:
        candidate = dedupe_key or trigger.dedupe_key
        if not candidate:
            return False
        return candidate == trigger.last_dedupe_key

    def list_due_triggers(
        self,
        workspace_id: str,
        *,
        now: Optional[datetime] = None,
    ) -> List[TriggerDefinition]:
        now = now or datetime.now(UTC)
        out: List[TriggerDefinition] = []

        for trigger in self.repository.list_all(workspace_id):
            if not trigger.enabled:
                continue
            if trigger.state != TriggerState.ACTIVE:
                continue
            if trigger.trigger_type != TriggerType.SCHEDULE:
                continue
            if not trigger.cadence_minutes:
                continue
            if self.should_skip_for_cooldown(trigger, now=now):
                continue

            next_run_at = parse_iso_datetime(trigger.next_run_at)
            if next_run_at is None:
                trigger.next_run_at = self.compute_next_run_at(
                    trigger,
                    now=now - timedelta(minutes=trigger.cadence_minutes),
                )
                trigger.updated_at = utc_now_iso()
                self.repository.save(trigger)
                next_run_at = parse_iso_datetime(trigger.next_run_at)

            if next_run_at is not None and next_run_at <= now:
                out.append(trigger)

        return out

    def mark_trigger_fired(
        self,
        trigger: TriggerDefinition,
        *,
        run_id: Optional[str],
        fired_at: Optional[datetime] = None,
        dedupe_key: Optional[str] = None,
    ) -> TriggerDefinition:
        fired_at = fired_at or datetime.now(UTC)
        fired_iso = fired_at.replace(microsecond=0).isoformat()

        trigger.last_attempted_at = fired_iso
        trigger.last_run_at = fired_iso
        trigger.last_run_id = run_id
        trigger.last_error = None
        trigger.run_count += 1

        candidate_dedupe = dedupe_key or trigger.dedupe_key
        if candidate_dedupe:
            trigger.last_dedupe_key = candidate_dedupe

        trigger.next_run_at = self.compute_next_run_at(trigger, now=fired_at)
        trigger.updated_at = utc_now_iso()
        return self.repository.save(trigger)

    def mark_trigger_completed(
        self,
        trigger: TriggerDefinition,
        *,
        completed_at: Optional[datetime] = None,
    ) -> TriggerDefinition:
        completed_at = completed_at or datetime.now(UTC)
        trigger.last_completed_at = completed_at.replace(microsecond=0).isoformat()
        trigger.updated_at = utc_now_iso()
        return self.repository.save(trigger)

    def mark_trigger_failed(
        self,
        trigger: TriggerDefinition,
        *,
        error: str,
        failed_at: Optional[datetime] = None,
    ) -> TriggerDefinition:
        failed_at = failed_at or datetime.now(UTC)
        trigger.last_attempted_at = failed_at.replace(microsecond=0).isoformat()
        trigger.last_error = error
        trigger.next_run_at = self.compute_next_run_at(trigger, now=failed_at)
        trigger.updated_at = utc_now_iso()
        return self.repository.save(trigger)

    def ensure_seed_schedule_trigger(
        self,
        *,
        workspace_id: str,
        trigger_id: str,
        workflow_definition_id: str,
        agent_definition_id: Optional[str],
        department_key: str,
        cadence_minutes: int,
        created_by: str = "system_seed",
        name: str = "Marketing Scheduled Draft Trigger",
    ) -> TriggerDefinition:
        existing = self.repository.load_optional(workspace_id, trigger_id)
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        model = TriggerDefinition(
            id=trigger_id,
            workspace_id=workspace_id,
            name=name,
            description="First-pass schedule trigger for marketing operator",
            trigger_type=TriggerType.SCHEDULE,
            enabled=True,
            workflow_definition_id=workflow_definition_id,
            agent_definition_id=agent_definition_id,
            department_key=department_key,
            cadence_minutes=cadence_minutes,
            cooldown_seconds=60,
            dedupe_key=f"{workspace_id}:{trigger_id}",
            next_run_at=(now + timedelta(minutes=cadence_minutes)).replace(
                microsecond=0
            ).isoformat(),
            created_by=created_by,
        )
        return self.repository.save(model)