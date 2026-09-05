from __future__ import annotations

import keyring

from backend.modules.aion_business.runtime.telephony_credentials import (
    RETELL_KEYCHAIN_SERVICE,
    get_retell_agent_id,
    get_retell_api_key,
    get_retell_from_number,
    retell_api_key_present,
    set_retell_api_key,
)


def test_retell_environment_key_takes_precedence(monkeypatch):
    monkeypatch.setenv("RETELL_API_KEY", "environment-key")
    monkeypatch.setattr(keyring, "get_password", lambda *_args: "keychain-key")

    assert get_retell_api_key("homefixed") == "environment-key"


def test_retell_workspace_key_precedes_default(monkeypatch):
    monkeypatch.delenv("RETELL_API_KEY", raising=False)

    def fake_get_password(service: str, account: str) -> str | None:
        assert service == RETELL_KEYCHAIN_SERVICE
        return {"homefixed": "workspace-key", "default": "default-key"}.get(account)

    monkeypatch.setattr(keyring, "get_password", fake_get_password)

    assert get_retell_api_key("homefixed") == "workspace-key"


def test_retell_default_key_is_development_fallback(monkeypatch):
    monkeypatch.delenv("RETELL_API_KEY", raising=False)
    monkeypatch.setattr(
        keyring,
        "get_password",
        lambda service, account: "default-key"
        if service == RETELL_KEYCHAIN_SERVICE and account == "default"
        else None,
    )

    assert get_retell_api_key("unknown-workspace") == "default-key"


def test_retell_nonsecret_runtime_values_prefer_environment(monkeypatch):
    monkeypatch.setenv("RETELL_AGENT_ID", "agent-env")
    monkeypatch.setenv("RETELL_FROM_NUMBER", "+34950000000")

    assert get_retell_agent_id("homefixed") == "agent-env"
    assert get_retell_from_number("homefixed") == "+34950000000"


def test_retell_key_is_written_to_workspace_keychain(monkeypatch):
    stored = []
    monkeypatch.setattr(keyring, "set_password", lambda service, account, value: stored.append((service, account, value)))

    set_retell_api_key("homefixed", "retell-secret")

    assert stored == [(RETELL_KEYCHAIN_SERVICE, "homefixed", "retell-secret")]


def test_retell_passive_presence_uses_environment_without_reading_keychain(monkeypatch):
    monkeypatch.setenv("RETELL_API_KEY", "environment-secret")
    monkeypatch.setattr(keyring, "get_password", lambda *_args: (_ for _ in ()).throw(AssertionError("secret read")))

    assert retell_api_key_present("homefixed") is True
