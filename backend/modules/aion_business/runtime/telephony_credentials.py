"""Server-side telephony credential lookup.

Environment variables remain supported for deployments.  On macOS desktop
installs, Retell API keys can instead live in Keychain so they are not written
to the repository or exposed to the renderer.  Workspace-specific credentials
take precedence over the development default, which keeps this lookup ready
for multi-business isolation.
"""

from __future__ import annotations

import os
import json
from pathlib import Path


RETELL_KEYCHAIN_SERVICE = "com.tessaris.sales.retell"
RETELL_DEPLOYMENT_PATH = Path(__file__).resolve().parents[4] / "data" / "local_vault" / "retell_homefixed_agent.json"


def get_retell_api_key(workspace_id: str | None = None) -> str:
    env_key = str(os.getenv("RETELL_API_KEY") or "").strip()
    if env_key:
        return env_key

    try:
        import keyring
    except Exception:
        return ""

    accounts = []
    workspace = str(workspace_id or "").strip()
    if workspace:
        accounts.append(workspace)
    accounts.append("default")

    for account in accounts:
        try:
            value = str(keyring.get_password(RETELL_KEYCHAIN_SERVICE, account) or "").strip()
        except Exception:
            value = ""
        if value:
            return value
    return ""


def _deployment() -> dict:
    if not RETELL_DEPLOYMENT_PATH.exists():
        return {}
    try:
        return json.loads(RETELL_DEPLOYMENT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_retell_agent_id(workspace_id: str | None = None) -> str:
    env_value = str(os.getenv("RETELL_AGENT_ID") or "").strip()
    if env_value:
        return env_value
    record = _deployment()
    return str(record.get("agent_id") or "").strip()


def get_retell_from_number(workspace_id: str | None = None) -> str:
    env_value = str(os.getenv("RETELL_FROM_NUMBER") or "").strip()
    if env_value:
        return env_value
    record = _deployment()
    return str(record.get("phone_number") or "").strip()
