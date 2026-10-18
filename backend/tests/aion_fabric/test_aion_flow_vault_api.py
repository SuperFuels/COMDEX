from __future__ import annotations

import base64
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


def test_guardian_binding_credentials_use_external_security_root(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "guardian")
    monkeypatch.setenv("TESSARIS_BUSINESS_VAULT_PATH", str(tmp_path / "vault"))
    monkeypatch.setenv("TESSARIS_BUSINESS_NAME", "Acme")
    monkeypatch.setenv("TESSARIS_BUSINESS_STABLE_ID", "acme")
    monkeypatch.setenv(
        "TESSARIS_BUSINESS_VAULT_KEY_B64",
        base64.b64encode(b"v" * 32).decode("ascii"),
    )
    monkeypatch.setenv("TESSARIS_APPLICATION_ROOT", str(tmp_path / "app"))
    monkeypatch.setenv("TESSARIS_UPDATE_ROOT", str(tmp_path / "updates"))
    monkeypatch.setenv("TESSARIS_DATA_ROOT", str(tmp_path / "application-data"))
    monkeypatch.setenv("TESSARIS_SECURITY_ROOT", str(tmp_path / "security"))

    bindings = vault_router._aion_flow_bindings("acme")
    assert bindings.root == (tmp_path / "security" / "aion-flow-model-bindings")
    assert bindings.domain_store is not None
    assert not str(bindings.root).startswith(str(tmp_path / "application-data"))
