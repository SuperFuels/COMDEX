from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.modules.aion_business.contracts.audit import (
    AuditEvent,
    MemoryAccessEvent,
    ProviderCallEvent,
    TraceEvent,
)
from backend.modules.aion_business.runtime.audit_repository import AuditRepository


router = APIRouter(prefix="/api/aion/business/audit", tags=["aion-business-audit"])


def get_audit_repository() -> AuditRepository:
    return AuditRepository()


@router.get("/{workspace_id}/events", response_model=List[AuditEvent])
def list_audit_events(
    workspace_id: str,
    event_type: Optional[str] = Query(default=None),
    role_id: Optional[str] = Query(default=None),
    agent_id: Optional[str] = Query(default=None),
    task_id: Optional[str] = Query(default=None),
    workflow_id: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=100, ge=1, le=1000),
):
    repo = get_audit_repository()
    return repo.list_events(
        workspace_id,
        event_type=event_type,
        role_id=role_id,
        agent_id=agent_id,
        task_id=task_id,
        workflow_id=workflow_id,
        limit=limit,
    )


@router.get("/{workspace_id}/events/{audit_id}", response_model=AuditEvent)
def get_audit_event(
    workspace_id: str,
    audit_id: str,
):
    repo = get_audit_repository()
    try:
        return repo.get_event(workspace_id, audit_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{workspace_id}/trace", response_model=List[TraceEvent])
def list_trace_events(
    workspace_id: str,
    trace_type: Optional[str] = Query(default=None),
    role_id: Optional[str] = Query(default=None),
    agent_id: Optional[str] = Query(default=None),
    task_id: Optional[str] = Query(default=None),
    workflow_id: Optional[str] = Query(default=None),
    stage: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=100, ge=1, le=1000),
):
    repo = get_audit_repository()
    return repo.list_trace(
        workspace_id,
        trace_type=trace_type,
        role_id=role_id,
        agent_id=agent_id,
        task_id=task_id,
        workflow_id=workflow_id,
        stage=stage,
        limit=limit,
    )


@router.get("/{workspace_id}/trace/{trace_id}", response_model=TraceEvent)
def get_trace_event(
    workspace_id: str,
    trace_id: str,
):
    repo = get_audit_repository()
    try:
        return repo.get_trace(workspace_id, trace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{workspace_id}/provider-calls", response_model=List[ProviderCallEvent])
def list_provider_calls(
    workspace_id: str,
    provider: Optional[str] = Query(default=None),
    capability: Optional[str] = Query(default=None),
    success: Optional[bool] = Query(default=None),
    role_id: Optional[str] = Query(default=None),
    agent_id: Optional[str] = Query(default=None),
    task_id: Optional[str] = Query(default=None),
    workflow_id: Optional[str] = Query(default=None),
    workflow_run_id: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=100, ge=1, le=1000),
):
    repo = get_audit_repository()
    return repo.list_provider_calls(
        workspace_id,
        provider=provider,
        capability=capability,
        success=success,
        role_id=role_id,
        agent_id=agent_id,
        task_id=task_id,
        workflow_id=workflow_id,
        workflow_run_id=workflow_run_id,
        limit=limit,
    )


@router.get("/{workspace_id}/provider-calls/{provider_call_id}", response_model=ProviderCallEvent)
def get_provider_call(
    workspace_id: str,
    provider_call_id: str,
):
    repo = get_audit_repository()
    try:
        return repo.get_provider_call(workspace_id, provider_call_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{workspace_id}/memory-access", response_model=List[MemoryAccessEvent])
def list_memory_access_events(
    workspace_id: str,
    binding_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    allowed: Optional[bool] = Query(default=None),
    role_id: Optional[str] = Query(default=None),
    agent_id: Optional[str] = Query(default=None),
    task_id: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=100, ge=1, le=1000),
):
    repo = get_audit_repository()
    return repo.list_memory_access(
        workspace_id,
        binding_id=binding_id,
        action=action,
        allowed=allowed,
        role_id=role_id,
        agent_id=agent_id,
        task_id=task_id,
        limit=limit,
    )


@router.get("/{workspace_id}/memory-access/{memory_access_id}", response_model=MemoryAccessEvent)
def get_memory_access_event(
    workspace_id: str,
    memory_access_id: str,
):
    repo = get_audit_repository()
    try:
        return repo.get_memory_access(workspace_id, memory_access_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc