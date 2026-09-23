"""
AION Agent Gateway v0 safety guards.

v0 is dry-run-only. Any attempted mutation, execution, provider call,
external write, booking, payment, escrow creation, or permission grant must
fail hard.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable


FORBIDDEN_DRY_RUN_ACTIONS = {
    "provider_call",
    "workflow_execution",
    "workflow_capsule_execution",
    "business_container_mutation",
    "active_repository_write",
    "external_write",
    "send_email",
    "send_whatsapp",
    "send_slack",
    "create_booking",
    "create_payment",
    "create_escrow",
    "grant_permission",
}


def assert_dry_run_only(*, dry_run_only: bool, attempted_action: str = "") -> None:
    action = str(attempted_action or "").strip()

    if dry_run_only is not True:
        raise RuntimeError("AION Gateway v0 requires dry_run_only=true.")

    if action and action in FORBIDDEN_DRY_RUN_ACTIONS:
        raise RuntimeError(
            f"AION Gateway v0 blocked forbidden dry-run action: {action}"
        )


def enforce_dry_run_only(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        dry_run_only = kwargs.get("dry_run_only", True)
        attempted_action = kwargs.get("attempted_action", "")
        assert_dry_run_only(
            dry_run_only=bool(dry_run_only),
            attempted_action=str(attempted_action or ""),
        )
        return fn(*args, **kwargs)

    return wrapper
