from __future__ import annotations

from typing import Any, Dict


def bootstrap_marketing_v1() -> Dict[str, Any]:
    """
    Bootstrap definition for the Phase 1 marketing operator/runtime surface.

    Keep this minimal first so the router can import successfully and the
    runtime can start. Expand later with real workflow/operator registration.
    """
    return {
        "ok": True,
        "operator_id": "operator_marketing_v1",
        "workflow_id": "workflow_marketing_content_draft_v1",
        "department_key": "marketing",
        "status": "bootstrapped",
    }