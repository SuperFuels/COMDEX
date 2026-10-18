from __future__ import annotations

import json
import os
import re


def parse_discovery_vault_roots(value: str) -> list[str]:
    """Accept the desktop JSON form and the legacy platform path-list form."""
    raw = str(value or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("discovery_vault_roots_invalid_json") from exc
        if not isinstance(decoded, list) or any(
            not isinstance(item, str) or not item.strip() for item in decoded
        ):
            raise ValueError("discovery_vault_roots_invalid_json")
        return [item.strip() for item in decoded]
    return [item for item in raw.split(os.pathsep) if item]


def parse_discovery_autostart(environment: dict[str, str]) -> tuple[str, str] | None:
    session_id = str(environment.get("TESSARIS_DISCOVERY_AUTOSTART_SESSION", "")).strip()
    scenario = str(environment.get("TESSARIS_DISCOVERY_AUTOSTART_SCENARIO", "")).strip()
    if not session_id and not scenario:
        return None
    if environment.get("TESSARIS_DISCOVERY_MODE") != "1":
        raise ValueError("discovery_autostart_requires_discovery_mode")
    safe = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    if safe.fullmatch(session_id) is None or safe.fullmatch(scenario) is None:
        raise ValueError("discovery_autostart_invalid")
    return session_id, scenario
