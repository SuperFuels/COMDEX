"""Workspace-scoped Twilio credential lookup for Tessaris Sales.

Deployments can use environment variables. The macOS application can instead
keep each business's credentials in Keychain, avoiding repository files and
preventing one customer's telephony account from leaking into another.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
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


def set_twilio_credentials(workspace_id: str, values: dict[str, str]) -> None:
    """Store workspace-scoped Twilio values in the operating-system vault."""
    try:
        import keyring
    except Exception as exc:
        raise RuntimeError("system_vault_unavailable") from exc
    workspace = str(workspace_id or "").strip()
    if not workspace:
        raise ValueError("workspace_id_required")
    allowed = {
        "account_sid": "account-sid",
        "api_key_sid": "api-key-sid",
        "api_key_secret": "api-key-secret",
        "from_number": "from-number",
        "carrier_number": "carrier-number",
        "caller_id": "caller-id",
        "trunk_sid": "trunk-sid",
        "termination_uri": "termination-uri",
        "sip_username": "sip-username",
        "sip_password": "sip-password",
    }
    for field, suffix in allowed.items():
        value = str(values.get(field) or "").strip()
        if value:
            keyring.set_password(TWILIO_KEYCHAIN_SERVICE, f"{workspace}.{suffix}", value)


def _keychain_item_exists(workspace_id: str | None, suffix: str) -> bool:
    """Check Keychain metadata without asking macOS to reveal the secret.

    ``keyring.get_password`` is deliberately not used here. Reading a password
    can display a macOS authorisation dialog, which is appropriate immediately
    before an approved provider action but not while rendering a status card.
    The ``security find-generic-password`` command, without ``-w`` or ``-g``,
    only checks whether the named item exists.
    """
    workspace = str(workspace_id or "").strip()
    security = Path("/usr/bin/security")
    if not workspace or not security.exists():
        return False
    try:
        result = subprocess.run(
            [
                str(security),
                "find-generic-password",
                "-s",
                TWILIO_KEYCHAIN_SERVICE,
                "-a",
                f"{workspace}.{suffix}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def get_twilio_credential_readiness(workspace_id: str | None = None) -> dict[str, Any]:
    """Return non-secret Twilio readiness suitable for passive UI rendering."""

    def present(suffix: str, *environment_names: str) -> bool:
        return any(str(os.getenv(name) or "").strip() for name in environment_names) or (
            _keychain_item_exists(workspace_id, suffix)
        )

    account = present("account-sid", "TWILIO_ACCOUNT_SID")
    username = present("api-key-sid", "TWILIO_API_KEY_SID") or account
    secret = present("api-key-secret", "TWILIO_API_KEY_SECRET", "TWILIO_AUTH_TOKEN")
    from_number = present("from-number", "TWILIO_FROM_NUMBER")
    carrier_number = present("carrier-number") or from_number
    caller_id = present("caller-id", "TWILIO_CALLER_ID")
    trunk = {
        suffix: present(suffix)
        for suffix in ("trunk-sid", "termination-uri", "sip-username", "sip-password")
    }
    credentials = bool(account and username and secret)
    return {
        "credential_ready": credentials,
        "configured": bool(credentials and from_number),
        "phone_number_configured": from_number,
        "carrier_number_configured": carrier_number,
        "verified_caller_id_configured": caller_id,
        "sip_trunk_configured": all(trunk.values()),
    }
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
