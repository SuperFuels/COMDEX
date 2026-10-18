from __future__ import annotations

import json
import os

import pytest

from backend.modules.aion_business.runtime.business_data_discovery_environment import (
    parse_discovery_autostart,
    parse_discovery_vault_roots,
)


def test_discovery_vault_roots_accept_desktop_json() -> None:
    assert parse_discovery_vault_roots(json.dumps(["/vault/one", "/vault/two"])) == [
        "/vault/one",
        "/vault/two",
    ]


def test_discovery_vault_roots_keep_legacy_path_list_compatibility() -> None:
    assert parse_discovery_vault_roots(os.pathsep.join(["/vault/one", "/vault/two"])) == [
        "/vault/one",
        "/vault/two",
    ]


@pytest.mark.parametrize("value", ["[]", '["/vault", 1]', '[""]', "[not-json"])
def test_discovery_vault_roots_reject_invalid_json(value: str) -> None:
    if value == "[]":
        assert parse_discovery_vault_roots(value) == []
        return
    with pytest.raises(ValueError, match="discovery_vault_roots_invalid_json"):
        parse_discovery_vault_roots(value)


def test_discovery_autostart_is_complete_safe_and_discovery_only() -> None:
    assert parse_discovery_autostart({}) is None
    assert parse_discovery_autostart({
        "TESSARIS_DISCOVERY_MODE": "1",
        "TESSARIS_DISCOVERY_AUTOSTART_SESSION": "business-onboarding",
        "TESSARIS_DISCOVERY_AUTOSTART_SCENARIO": "create-business-through-onboarding-pilot",
    }) == ("business-onboarding", "create-business-through-onboarding-pilot")
    with pytest.raises(ValueError, match="discovery_autostart_requires_discovery_mode"):
        parse_discovery_autostart({
            "TESSARIS_DISCOVERY_MODE": "0",
            "TESSARIS_DISCOVERY_AUTOSTART_SESSION": "business-onboarding",
            "TESSARIS_DISCOVERY_AUTOSTART_SCENARIO": "create-business-through-onboarding-pilot",
        })
    with pytest.raises(ValueError, match="discovery_autostart_invalid"):
        parse_discovery_autostart({
            "TESSARIS_DISCOVERY_MODE": "1",
            "TESSARIS_DISCOVERY_AUTOSTART_SESSION": "business-onboarding",
        })
