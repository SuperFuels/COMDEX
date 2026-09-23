from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.modules.aion_business.contracts.audit import (
    AuditEvent,
    MemoryAccessEvent,
    ProviderCallEvent,
    TraceEvent,
)
from backend.modules.aion_business.runtime.audit_log import AuditLog


class AuditRepository:
    """
    Read/query layer over the JSONL-backed AuditLog.

    Keeps write logic in AuditLog and gives API/services a stable place to:
    - list event streams
    - filter by role / agent / task / workflow
    - read specific audit record ids
    """

    def __init__(self, audit_log: Optional[AuditLog] = None):
        self.audit_log = audit_log or AuditLog()

    def list_events(
        self,
        workspace_id: str,
        *,
        event_type: Optional[str] = None,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        rows = self.audit_log.read_stream(workspace_id, "events")
        out = [AuditEvent(**row) for row in rows]
        out = self._filter_common(
            out,
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            workflow_id=workflow_id,
        )

        if event_type:
            out = [row for row in out if row.event_type == event_type]

        return self._sort_and_limit(out, limit=limit)

    def list_trace(
        self,
        workspace_id: str,
        *,
        trace_type: Optional[str] = None,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        stage: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[TraceEvent]:
        rows = self.audit_log.read_stream(workspace_id, "trace")
        out = [TraceEvent(**row) for row in rows]
        out = self._filter_common(
            out,
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            workflow_id=workflow_id,
        )

        if trace_type:
            out = [row for row in out if row.trace_type == trace_type]
        if stage:
            out = [row for row in out if row.stage == stage]

        return self._sort_and_limit(out, limit=limit)

    def list_provider_calls(
        self,
        workspace_id: str,
        *,
        provider: Optional[str] = None,
        capability: Optional[str] = None,
        success: Optional[bool] = None,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        workflow_run_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ProviderCallEvent]:
        rows = self.audit_log.read_stream(workspace_id, "provider_calls")
        out = [ProviderCallEvent(**row) for row in rows]
        out = self._filter_common(
            out,
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            workflow_id=workflow_id,
        )

        if provider:
            out = [row for row in out if row.provider == provider]
        if capability:
            out = [row for row in out if row.capability == capability]
        if success is not None:
            out = [row for row in out if row.success is success]
        if workflow_run_id:
            out = [row for row in out if row.workflow_run_id == workflow_run_id]

        return self._sort_and_limit(out, limit=limit)

    def list_memory_access(
        self,
        workspace_id: str,
        *,
        binding_id: Optional[str] = None,
        action: Optional[str] = None,
        allowed: Optional[bool] = None,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[MemoryAccessEvent]:
        rows = self.audit_log.read_stream(workspace_id, "memory_access")
        out = [MemoryAccessEvent(**row) for row in rows]

        if role_id:
            out = [row for row in out if row.role_id == role_id]
        if agent_id:
            out = [row for row in out if row.agent_id == agent_id]
        if task_id:
            out = [row for row in out if row.task_id == task_id]
        if binding_id:
            out = [row for row in out if row.binding_id == binding_id]
        if action:
            out = [row for row in out if row.action == action]
        if allowed is not None:
            out = [row for row in out if row.allowed is allowed]

        return self._sort_and_limit(out, limit=limit)

    def get_event(self, workspace_id: str, audit_id: str) -> AuditEvent:
        for row in self.list_events(workspace_id):
            if row.id == audit_id:
                return row
        raise FileNotFoundError(f"Audit event not found: {workspace_id}/{audit_id}")

    def get_trace(self, workspace_id: str, trace_id: str) -> TraceEvent:
        for row in self.list_trace(workspace_id):
            if row.id == trace_id:
                return row
        raise FileNotFoundError(f"Trace event not found: {workspace_id}/{trace_id}")

    def get_provider_call(self, workspace_id: str, provider_call_id: str) -> ProviderCallEvent:
        for row in self.list_provider_calls(workspace_id):
            if row.id == provider_call_id:
                return row
        raise FileNotFoundError(
            f"Provider call event not found: {workspace_id}/{provider_call_id}"
        )

    def get_memory_access(self, workspace_id: str, memory_access_id: str) -> MemoryAccessEvent:
        for row in self.list_memory_access(workspace_id):
            if row.id == memory_access_id:
                return row
        raise FileNotFoundError(
            f"Memory access event not found: {workspace_id}/{memory_access_id}"
        )

    @staticmethod
    def _filter_common(
        rows: List[Any],
        *,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> List[Any]:
        out = rows

        if role_id:
            out = [row for row in out if getattr(row, "role_id", None) == role_id]
        if agent_id:
            out = [row for row in out if getattr(row, "agent_id", None) == agent_id]
        if task_id:
            out = [row for row in out if getattr(row, "task_id", None) == task_id]
        if workflow_id:
            out = [row for row in out if getattr(row, "workflow_id", None) == workflow_id]

        return out

    @staticmethod
    def _sort_and_limit(rows: List[Any], *, limit: Optional[int] = None) -> List[Any]:
        out = sorted(
            rows,
            key=lambda row: getattr(row, "created_at", ""),
            reverse=True,
        )
        if limit is not None:
            out = out[:limit]
        return out