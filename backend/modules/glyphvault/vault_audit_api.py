# backend/modules/glyphvault/vault_audit_api.py

from fastapi import APIRouter, Query
from typing import List, Dict, Any

from backend.modules.glyphvault.vault_audit import VAULT_AUDIT

router = APIRouter()

@router.get("/vault/audit/logs", response_model=List[Dict[str, Any]])
def get_audit_logs(limit: int = Query(100, ge=1, le=1000)):
    """
    Retrieve recent vault audit logs, newest first.

    Args:
        limit (int): Number of log entries to return (default 100, max 1000)

    Returns:
        List of audit log entries with timestamp, event_type, container_id, user_id, and extra metadata.
    """
    return VAULT_AUDIT.get_recent_logs(limit)

@router.get("/vault/audit/metrics")
def get_audit_metrics():
    """
    Retrieve current vault audit metrics summary.

    Returns:
        Dictionary with counts of save, restore, delete, and access denied events.
    """
    return VAULT_AUDIT.get_metrics()