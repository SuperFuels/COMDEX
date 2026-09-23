from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from backend.api import vault_router


def test_visual_picker_api_returns_only_public_binding_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSARIS_DATA_ROOT", str(tmp_path))
    payload = vault_router.AionFlowBindingCreateRequest(
        binding_id="gemini-research",
        provider="gemini",
        label="Gemini research",
        secret="private-test-key",
    )
    created = vault_router.create_aion_flow_binding(
        payload,
        x_aion_vault_intent="create-aion-flow-binding-v1",
    )
    assert created["binding"]["reference"] == "vault://model/gemini-research"
    assert created["raw_secret_returned"] is False

    listed = vault_router.list_aion_flow_bindings()
    encoded = json.dumps(listed)
    assert listed["raw_secrets_exposed"] is False
    assert listed["bindings"][0]["label"] == "Gemini research"
    assert "private-test-key" not in encoded


def test_visual_picker_api_requires_explicit_local_vault_intent(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSARIS_DATA_ROOT", str(tmp_path))
    payload = vault_router.AionFlowBindingCreateRequest(
        binding_id="private-endpoint",
        provider="private_endpoint",
        secret="private-test-key",
    )
    with pytest.raises(HTTPException) as error:
        vault_router.create_aion_flow_binding(payload, x_aion_vault_intent="")
    assert error.value.status_code == 403
