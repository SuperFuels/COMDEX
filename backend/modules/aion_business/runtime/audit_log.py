from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_business.contracts.audit import (
    AuditEvent,
    MemoryAccessEvent,
    ProviderCallEvent,
    TraceEvent,
)
from backend.modules.aion_business.providers.contracts import (
    ProviderRequest,
    ProviderResult,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class AuditLog:
    """
    JSONL-backed audit log for Aion Business.

    Streams:
    - events
    - trace
    - provider_calls
    - memory_access
    """

    def __init__(self) -> None:
        AIONBusinessPaths.ensure_base_dirs()

    def _audit_dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.ROOT / "audit" / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _audit_file(self, workspace_id: str, stream: str) -> Path:
        return self._audit_dir(workspace_id) / f"{stream}.jsonl"

    def _append_jsonl(self, path: Path, payload: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def append_event(self, event: AuditEvent) -> None:
        self._append_jsonl(
            self._audit_file(event.workspace_id, "events"),
            event.model_dump(mode="json"),
        )

    def append_trace(self, event: TraceEvent) -> None:
        self._append_jsonl(
            self._audit_file(event.workspace_id, "trace"),
            event.model_dump(mode="json"),
        )

    def append_provider_call(self, event: ProviderCallEvent) -> None:
        self._append_jsonl(
            self._audit_file(event.workspace_id, "provider_calls"),
            event.model_dump(mode="json"),
        )

    def append_memory_access(self, event: MemoryAccessEvent) -> None:
        self._append_jsonl(
            self._audit_file(event.workspace_id, "memory_access"),
            event.model_dump(mode="json"),
        )

    def log_event(
        self,
        *,
        workspace_id: str,
        event_type: str,
        summary: str,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=f"audit-{secrets.token_hex(8)}",
            workspace_id=workspace_id,
            event_type=event_type,
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            workflow_id=workflow_id,
            summary=summary,
            payload=payload or {},
            tags=tags or [],
        )
        self.append_event(event)
        return event

    def log_trace(
        self,
        *,
        workspace_id: str,
        trace_type: str,
        message: str,
        stage: Optional[str] = None,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        event = TraceEvent(
            id=f"trace-{secrets.token_hex(8)}",
            workspace_id=workspace_id,
            trace_type=trace_type,
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            workflow_id=workflow_id,
            stage=stage,
            message=message,
            data=data or {},
        )
        self.append_trace(event)
        return event

    def log_memory_access(
        self,
        *,
        workspace_id: str,
        binding_id: str,
        action: str,
        allowed: bool,
        reason: str,
        scope: Optional[str] = None,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryAccessEvent:
        event = MemoryAccessEvent(
            id=f"mem-{secrets.token_hex(8)}",
            workspace_id=workspace_id,
            binding_id=binding_id,
            action=action,
            allowed=allowed,
            reason=reason,
            scope=scope,
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            metadata=metadata or {},
        )
        self.append_memory_access(event)
        return event

    def log_provider_call(
        self,
        *,
        workspace_id: str,
        provider: str,
        request_summary: str,
        success: bool,
        capability: Optional[str] = None,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        workflow_run_id: Optional[str] = None,
        model_policy_ref: Optional[str] = None,
        model: Optional[str] = None,
        response_summary: Optional[str] = None,
        prompt_preview: Optional[str] = None,
        usage: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        latency_ms: int = 0,
        fallback_used: bool = False,
        cost_estimate: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProviderCallEvent:
        event = ProviderCallEvent(
            id=f"prov-{secrets.token_hex(8)}",
            workspace_id=workspace_id,
            provider=provider,
            capability=capability,
            actor_id=None,
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            model_policy_ref=model_policy_ref,
            model=model,
            request_summary=request_summary,
            response_summary=response_summary,
            prompt_preview=prompt_preview,
            success=success,
            error_code=error_code,
            usage=usage or {},
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            cost_estimate=cost_estimate,
            metadata=metadata or {},
        )
        self.append_provider_call(event)
        return event

    def log_provider_call_from_contracts(
        self,
        *,
        workspace_id: str,
        request: ProviderRequest,
        result: ProviderResult,
        role_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        workflow_run_id: Optional[str] = None,
    ) -> ProviderCallEvent:
        request_summary = (
            f"provider={request.provider}; "
            f"capability={request.capability}; "
            f"skill_id={request.skill_id}; "
            f"role_type={request.role_type}; "
            f"model={request.model or 'default'}"
        )

        response_summary = result.content[:200] if result.content else None
        prompt_preview = request.prompt[:200] if request.prompt else None

        metadata = {
            **dict(request.metadata or {}),
            "skill_id": request.skill_id,
            "role_type": request.role_type,
            "warnings": list(result.warnings or []),
            "raw": result.raw,
        }

        resolved_workflow_id = workflow_id or metadata.get("workflow_id")
        resolved_workflow_run_id = workflow_run_id or metadata.get("workflow_run_id")

        return self.log_provider_call(
            workspace_id=workspace_id,
            provider=result.provider or request.provider,
            request_summary=request_summary,
            success=result.ok,
            capability=request.capability,
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            workflow_id=resolved_workflow_id,
            workflow_run_id=resolved_workflow_run_id,
            model_policy_ref=result.policy_id or request.policy_id,
            model=result.model,
            response_summary=response_summary,
            prompt_preview=prompt_preview,
            usage=dict(result.usage or {}),
            error_code=result.error_code,
            latency_ms=result.latency_ms,
            fallback_used=result.fallback_used,
            cost_estimate=0.0,
            metadata=metadata,
        )

    def log_agent_transition(
        self,
        *,
        workspace_id: str,
        role_id: Optional[str],
        agent_id: str,
        task_id: Optional[str],
        from_state: str,
        to_state: str,
    ) -> AuditEvent:
        return self.log_event(
            workspace_id=workspace_id,
            event_type="agent_transition",
            role_id=role_id,
            agent_id=agent_id,
            task_id=task_id,
            summary=f"Agent transitioned from {from_state} to {to_state}",
            payload={
                "from_state": from_state,
                "to_state": to_state,
            },
            tags=["agent", "lifecycle", to_state],
        )

    def read_stream(
        self,
        workspace_id: str,
        stream: str,
    ) -> List[Dict[str, Any]]:
        path = self._audit_file(workspace_id, stream)
        if not path.exists():
            return []

        out: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                out.append(json.loads(line))
        return out