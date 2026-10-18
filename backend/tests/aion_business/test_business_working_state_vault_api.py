from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.modules.aion_business.api import business_twin_data_api as api
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _guardian(monkeypatch, tmp_path) -> VaultGuardian:
    layout = provision_business_vault(
        tmp_path / "vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id="acme", encryption_key=b"w" * 32
    )
    monkeypatch.setattr(api, "guardian_mode_requested", lambda: True)
    monkeypatch.setattr(
        api,
        "configured_business_vault_runtime",
        lambda: SimpleNamespace(guardian=guardian),
    )
    return guardian


def test_business_working_state_round_trip_is_encrypted_versioned_and_deletable(
    monkeypatch, tmp_path
):
    guardian = _guardian(monkeypatch, tmp_path)
    request = api.BusinessWorkingStateWriteRequest(
        payload={
            "storage_key": "aion.chat.sessions.v3",
            "value": {"chat-1": {"messages": ["Private customer discussion"]}},
        },
        expected_version=0,
    )
    saved = api.put_business_working_state("acme", "aion.chat.sessions.v3", request)
    assert saved["version"] == 1
    loaded = api.get_business_working_state("acme", "aion.chat.sessions.v3")
    assert loaded["payload"]["value"]["value"]["chat-1"]["messages"] == [
        "Private customer discussion"
    ]
    assert api.list_business_working_state("acme")["states"][0]["state_id"] == (
        "aion.chat.sessions.v3"
    )
    assert b"Private customer discussion" not in guardian.database.read_bytes()

    with pytest.raises(HTTPException) as conflict:
        api.put_business_working_state(
            "acme",
            "aion.chat.sessions.v3",
            api.BusinessWorkingStateWriteRequest(
                payload={"storage_key": "aion.chat.sessions.v3", "value": {}},
                expected_version=0,
            ),
        )
    assert conflict.value.status_code == 409

    assert api.delete_business_working_state("acme", "aion.chat.sessions.v3")[
        "deleted"
    ] is True
    with pytest.raises(HTTPException) as missing:
        api.get_business_working_state("acme", "aion.chat.sessions.v3")
    assert missing.value.status_code == 404


def test_business_working_state_rejects_unsafe_identity_and_oversized_payload(
    monkeypatch, tmp_path
):
    _guardian(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as invalid:
        api.put_business_working_state(
            "acme",
            "../outside",
            api.BusinessWorkingStateWriteRequest(payload={}),
        )
    assert invalid.value.status_code == 400

    with pytest.raises(HTTPException) as oversized:
        api.put_business_working_state(
            "acme",
            "large-state",
            api.BusinessWorkingStateWriteRequest(
                payload={"value": "x" * (api._MAX_WORKING_STATE_BYTES + 1)}
            ),
        )
    assert oversized.value.status_code == 413
