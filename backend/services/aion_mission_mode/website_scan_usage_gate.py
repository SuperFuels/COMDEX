"""AION Phase 24B — Website scan usage gate.

Production can require login before website scans consume provider credits.
Local dev remains allowed unless AION_REQUIRE_SCAN_LOGIN=1.
"""

from __future__ import annotations

import os
from typing import Any


def website_scan_allowed(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    require_login = os.getenv("AION_REQUIRE_SCAN_LOGIN", "0") == "1"

    user_ref = (
        payload.get("user_id")
        or payload.get("account_id")
        or payload.get("session_id")
        or payload.get("signed_in_user_id")
    )

    if require_login and not user_ref:
        return {
            "allowed": False,
            "reason": "login_required_before_openai_scan",
        }

    return {
        "allowed": True,
        "reason": "allowed",
        "user_ref": str(user_ref or "local_dev"),
    }
