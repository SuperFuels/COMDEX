"""Workspace-scoped Twilio credential lookup for Tessaris Sales.

Deployments can use environment variables. The macOS application can instead
keep each business's credentials in Keychain, avoiding repository files and
preventing one customer's telephony account from leaking into another.
"""

from __future__ import annotations

import os
from typing import Any


TWILIO_KEYCHAIN_SERVICE = "com.tessaris.sales.twilio"


def _keychain(workspace_id: str | None, suffix: str) -> str:
    try:
        import keyring
    except Exception:
        return ""
    workspace = str(workspace_id or "").strip()
    if not workspace:
        return ""
    try:
        return str(
            keyring.get_password(TWILIO_KEYCHAIN_SERVICE, f"{workspace}.{suffix}") or ""
        ).strip()
    except Exception:
        return ""


def get_twilio_account_sid(workspace_id: str | None = None) -> str:
    return str(os.getenv("TWILIO_ACCOUNT_SID") or "").strip() or _keychain(
        workspace_id, "account-sid"
    )


def get_twilio_api_username(workspace_id: str | None = None) -> str:
    return (
        str(os.getenv("TWILIO_API_KEY_SID") or "").strip()
        or _keychain(workspace_id, "api-key-sid")
        or get_twilio_account_sid(workspace_id)
    )


def get_twilio_api_secret(workspace_id: str | None = None) -> str:
    return (
        str(os.getenv("TWILIO_API_KEY_SECRET") or "").strip()
        or _keychain(workspace_id, "api-key-secret")
        or str(os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
    )


def get_twilio_from_number(workspace_id: str | None = None) -> str:
    return str(os.getenv("TWILIO_FROM_NUMBER") or "").strip() or _keychain(
        workspace_id, "from-number"
    )


def get_twilio_carrier_number(workspace_id: str | None = None) -> str:
    return _keychain(workspace_id, "carrier-number") or get_twilio_from_number(workspace_id)


def get_twilio_caller_id(workspace_id: str | None = None) -> str:
    return str(os.getenv("TWILIO_CALLER_ID") or "").strip() or _keychain(
        workspace_id, "caller-id"
    )


def get_twilio_trunk(workspace_id: str | None = None) -> dict[str, Any]:
    return {
        "trunk_sid": _keychain(workspace_id, "trunk-sid"),
        "termination_uri": _keychain(workspace_id, "termination-uri"),
        "sip_username": _keychain(workspace_id, "sip-username"),
        "sip_password": _keychain(workspace_id, "sip-password"),
    }
