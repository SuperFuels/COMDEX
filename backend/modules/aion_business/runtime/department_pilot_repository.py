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
from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


class DepartmentPilotConcurrencyError(RuntimeError):
    pass


class DepartmentPilotRepository:
    """Persist one immutable-hash envelope per task with compare-and-swap updates."""

    def __init__(
        self,
        base_dir: str | Path | None = None,
        *,
        domain_store: VaultDomainStore | None = None,
    ) -> None:
        self.base_dir = (
            Path(base_dir) if base_dir is not None else AIONBusinessPaths.DEPARTMENT_PILOT_RUNTIME
        )
        self.domain_store = domain_store
        if self.domain_store is None and base_dir is None and guardian_mode_requested():
            self.domain_store = VaultDomainStore(
                configured_business_vault_runtime().guardian,
                actor_id="department-pilot-runtime",
            )
        if self.domain_store is None:
            self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _entity_id(department_id: str, task_id: str) -> str:
        return f"{department_id}/{task_id}"

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
        if self.domain_store is not None:
            entity_id = self._entity_id(envelope.task.department_id, envelope.task.task_id)
            if self.domain_store.get_optional(
                "departments.pilot_tasks",
                workspace_id=envelope.task.workspace_id,
                entity_id=entity_id,
            ) is not None:
                raise FileExistsError("Department Pilot task already exists")
            result = self.domain_store.put(
                "departments.pilot_tasks",
                workspace_id=envelope.task.workspace_id,
                entity_id=entity_id,
                payload=envelope.model_dump(mode="json"),
                expected_version=None,
                idempotency_key=f"department-task-create-{envelope.envelope_hash.removeprefix('sha256:')[:32]}",
            )
            self._append_audit(envelope, "created")
            return f"guardian://department_pilot_tasks/{result['record_id']}?version={result['version']}"
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
        if self.domain_store is not None:
            entity_id = self._entity_id(envelope.task.department_id, envelope.task.task_id)
            record = self.domain_store.get(
                "departments.pilot_tasks",
                workspace_id=envelope.task.workspace_id,
                entity_id=entity_id,
            )
            current = DepartmentPilotWorkEnvelope.model_validate(record["payload"])
            if current.envelope_hash != expected_previous_hash:
                raise DepartmentPilotConcurrencyError(
                    "department_pilot_stale_write:"
                    f"expected={expected_previous_hash}:actual={current.envelope_hash}"
                )
            result = self.domain_store.put(
                "departments.pilot_tasks",
                workspace_id=envelope.task.workspace_id,
                entity_id=entity_id,
                payload=envelope.model_dump(mode="json"),
                expected_version=int(record["version"]),
                idempotency_key=f"department-task-update-{envelope.envelope_hash.removeprefix('sha256:')[:32]}",
            )
            self._append_audit(envelope, "updated", previous_hash=current.envelope_hash)
            return f"guardian://department_pilot_tasks/{result['record_id']}?version={result['version']}"
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
        if self.domain_store is not None:
            try:
                record = self.domain_store.get(
                    "departments.pilot_tasks",
                    workspace_id=workspace_id,
                    entity_id=self._entity_id(department_id, task_id),
                )
            except KeyError as exc:
                raise FileNotFoundError("Department Pilot task not found") from exc
            return DepartmentPilotWorkEnvelope.model_validate(record["payload"])
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
        if self.domain_store is not None:
            envelopes = [
                DepartmentPilotWorkEnvelope.model_validate(record["payload"])
                for record in self.domain_store.list(
                    "departments.pilot_tasks", workspace_id=workspace_id
                )
                if str(record.get("entity_id") or "").startswith(f"{department_id}/")
            ]
            return [item for item in envelopes if not allowed or item.task.status in allowed]
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
        if self.domain_store is not None:
            allowed = set(statuses or [])
            envelopes = [
                DepartmentPilotWorkEnvelope.model_validate(record["payload"])
                for record in self.domain_store.list(
                    "departments.pilot_tasks", workspace_id=workspace_id
                )
            ]
            filtered = [item for item in envelopes if not allowed or item.task.status in allowed]
            return sorted(filtered, key=lambda item: (item.task.department_id, item.task.task_id))
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
        if self.domain_store is not None:
            event_id = f"{envelope.task.department_id}/{envelope.task.task_id}/{operation}/{envelope.envelope_hash}"
            self.domain_store.put(
                "departments.pilot_audit",
                workspace_id=envelope.task.workspace_id,
                entity_id=event_id,
                payload=record,
                expected_version=None,
                idempotency_key=f"department-audit-{envelope.envelope_hash.removeprefix('sha256:')[:24]}-{operation}",
            )
            return
        path = self.audit_path(envelope.task.workspace_id, envelope.task.department_id)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
