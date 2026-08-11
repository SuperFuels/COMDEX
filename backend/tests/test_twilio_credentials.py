from __future__ import annotations

import keyring

from backend.modules.aion_business.runtime.twilio_credentials import (
    TWILIO_KEYCHAIN_SERVICE,
    get_twilio_account_sid,
    get_twilio_api_secret,
    get_twilio_api_username,
    get_twilio_caller_id,
    get_twilio_carrier_number,
    get_twilio_from_number,
    get_twilio_trunk,
)


def test_twilio_environment_credentials_take_precedence(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC-environment")
    monkeypatch.setenv("TWILIO_API_KEY_SID", "SK-environment")
    monkeypatch.setenv("TWILIO_API_KEY_SECRET", "secret-environment")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+34950000000")
    monkeypatch.setattr(keyring, "get_password", lambda *_args: "keychain-value")

    assert get_twilio_account_sid("home-fixed") == "AC-environment"
    assert get_twilio_api_username("home-fixed") == "SK-environment"
    assert get_twilio_api_secret("home-fixed") == "secret-environment"
    assert get_twilio_from_number("home-fixed") == "+34950000000"


def test_twilio_workspace_credentials_are_isolated(monkeypatch):
    for name in (
        "TWILIO_ACCOUNT_SID", "TWILIO_API_KEY_SID", "TWILIO_API_KEY_SECRET",
        "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER",
    ):
        monkeypatch.delenv(name, raising=False)

    values = {
        "home-fixed.account-sid": "AC-home-fixed",
        "home-fixed.api-key-sid": "SK-home-fixed",
        "home-fixed.api-key-secret": "secret-home-fixed",
        "home-fixed.from-number": "+34711269364",
        "home-fixed.carrier-number": "+18576885613",
        "home-fixed.caller-id": "+34711269364",
        "another-business.account-sid": "AC-another",
    }

    def fake_get_password(service: str, account: str) -> str | None:
        assert service == TWILIO_KEYCHAIN_SERVICE
        return values.get(account)

    monkeypatch.setattr(keyring, "get_password", fake_get_password)

    assert get_twilio_account_sid("home-fixed") == "AC-home-fixed"
    assert get_twilio_account_sid("another-business") == "AC-another"
    assert get_twilio_api_username("home-fixed") == "SK-home-fixed"
    assert get_twilio_api_secret("home-fixed") == "secret-home-fixed"
    assert get_twilio_from_number("home-fixed") == "+34711269364"
    assert get_twilio_carrier_number("home-fixed") == "+18576885613"
    assert get_twilio_caller_id("home-fixed") == "+34711269364"


def test_twilio_trunk_reads_workspace_keychain(monkeypatch):
    values = {
        "home-fixed.trunk-sid": "TK-test",
        "home-fixed.termination-uri": "tessaris-homefixed-retell.pstn.twilio.com",
        "home-fixed.sip-username": "homefixed-test",
        "home-fixed.sip-password": "secret-test",
    }
    monkeypatch.setattr(
        keyring,
        "get_password",
        lambda service, account: values.get(account)
        if service == TWILIO_KEYCHAIN_SERVICE else None,
    )

    assert get_twilio_trunk("home-fixed") == {
        "trunk_sid": "TK-test",
        "termination_uri": "tessaris-homefixed-retell.pstn.twilio.com",
        "sip_username": "homefixed-test",
        "sip_password": "secret-test",
    }
