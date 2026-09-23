"""Backend-authoritative persistence for Department Pilot work envelopes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from backend.modules.aion_business.contracts.department_pilot import (
    DepartmentId,
    DepartmentPilotWorkEnvelope,
    TaskStatus,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class DepartmentPilotConcurrencyError(RuntimeError):
    pass


class DepartmentPilotRepository:
    """Persist one immutable-hash envelope per task with compare-and-swap updates."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = (
            Path(base_dir) if base_dir is not None else AIONBusinessPaths.DEPARTMENT_PILOT_RUNTIME
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _department_dir(self, workspace_id: str, department_id: str) -> Path:
        path = self.base_dir / workspace_id / department_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _task_dir(self, workspace_id: str, department_id: str) -> Path:
        path = self._department_dir(workspace_id, department_id) / "tasks"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def task_path(self, workspace_id: str, department_id: str, task_id: str) -> Path:
        return self._task_dir(workspace_id, department_id) / f"{task_id}.json"

    def audit_path(self, workspace_id: str, department_id: str) -> Path:
        return self._department_dir(workspace_id, department_id) / "audit.jsonl"

    @staticmethod
    def _atomic_write(path: Path, payload: dict) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def create(self, envelope: DepartmentPilotWorkEnvelope) -> str:
        path = self.task_path(
            envelope.task.workspace_id, envelope.task.department_id, envelope.task.task_id
        )
        if path.exists():
            raise FileExistsError(f"Department Pilot task already exists: {path}")
        self._atomic_write(path, envelope.model_dump(mode="json"))
        self._append_audit(envelope, "created")
        return str(path)

    def save(
        self,
        envelope: DepartmentPilotWorkEnvelope,
        *,
        expected_previous_hash: str,
    ) -> str:
        path = self.task_path(
            envelope.task.workspace_id, envelope.task.department_id, envelope.task.task_id
        )
        if not path.exists():
            raise FileNotFoundError(f"Department Pilot task not found: {path}")
        current = self.load(
            envelope.task.workspace_id, envelope.task.department_id, envelope.task.task_id
        )
        if current.envelope_hash != expected_previous_hash:
            raise DepartmentPilotConcurrencyError(
                "department_pilot_stale_write:" f"expected={expected_previous_hash}:actual={current.envelope_hash}"
            )
        self._atomic_write(path, envelope.model_dump(mode="json"))
        self._append_audit(envelope, "updated", previous_hash=current.envelope_hash)
        return str(path)

    def load(
        self, workspace_id: str, department_id: str, task_id: str
    ) -> DepartmentPilotWorkEnvelope:
        path = self.task_path(workspace_id, department_id, task_id)
        if not path.exists():
            raise FileNotFoundError(f"Department Pilot task not found: {path}")
        return DepartmentPilotWorkEnvelope.model_validate_json(path.read_text(encoding="utf-8"))

    def list_for_department(
        self,
        workspace_id: str,
        department_id: DepartmentId,
        *,
        statuses: Optional[Iterable[TaskStatus]] = None,
    ) -> list[DepartmentPilotWorkEnvelope]:
        allowed = set(statuses or [])
        envelopes: list[DepartmentPilotWorkEnvelope] = []
        for path in sorted(self._task_dir(workspace_id, department_id).glob("*.json")):
            envelope = DepartmentPilotWorkEnvelope.model_validate_json(
                path.read_text(encoding="utf-8")
            )
            if not allowed or envelope.task.status in allowed:
                envelopes.append(envelope)
        return envelopes

    def list_for_workspace(
        self,
        workspace_id: str,
        *,
        statuses: Optional[Iterable[TaskStatus]] = None,
    ) -> list[DepartmentPilotWorkEnvelope]:
        workspace_dir = self.base_dir / workspace_id
        if not workspace_dir.exists():
            return []
        envelopes: list[DepartmentPilotWorkEnvelope] = []
        for department_dir in sorted(path for path in workspace_dir.iterdir() if path.is_dir()):
            envelopes.extend(
                self.list_for_department(
                    workspace_id,
                    department_dir.name,  # type: ignore[arg-type]
                    statuses=statuses,
                )
            )
        return sorted(envelopes, key=lambda item: (item.task.department_id, item.task.task_id))

    def _append_audit(
        self,
        envelope: DepartmentPilotWorkEnvelope,
        operation: str,
        *,
        previous_hash: str | None = None,
    ) -> None:
        record = {
            "schema_version": "aion.department_pilot.repository_audit.v1",
            "operation": operation,
            "workspace_id": envelope.task.workspace_id,
            "business_id": envelope.task.business_id,
            "department_id": envelope.task.department_id,
            "task_id": envelope.task.task_id,
            "task_status": envelope.task.status,
            "previous_envelope_hash": previous_hash,
            "envelope_hash": envelope.envelope_hash,
            "event_count": len(envelope.events),
            "receipt_count": len(envelope.receipts),
        }
        path = self.audit_path(envelope.task.workspace_id, envelope.task.department_id)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
