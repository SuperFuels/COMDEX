from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.aion_flow_model_bindings import AionFlowModelBindings


def test_binding_keeps_secret_in_encrypted_vault_and_exposes_only_stable_reference(tmp_path):
    bindings = AionFlowModelBindings(tmp_path / "bindings")
    public = bindings.create(
        binding_id="gemini-primary",
        provider="gemini",
        secret="private-provider-key",
        label="Gemini key",
    )
    assert public["reference"] == "vault://model/gemini-primary"
    assert public["secret_exposed"] is False
    assert bindings.resolve(public["reference"]) == "private-provider-key"
    assert "private-provider-key" not in bindings.state_path.read_text(encoding="utf-8")
    assert "private-provider-key" not in json.dumps(bindings.public_bindings())


def test_rotation_preserves_workflow_reference_and_revocation_fails_closed(tmp_path):
    bindings = AionFlowModelBindings(tmp_path / "bindings")
    original = bindings.create(binding_id="private-model", provider="customer", secret="first-secret")
    rotated = bindings.rotate(original["reference"], secret="second-secret")
    assert rotated["reference"] == original["reference"]
    assert rotated["revision"] == 2
    assert bindings.resolve(original["reference"]) == "second-secret"
    revoked = bindings.revoke(original["reference"])
    assert revoked["status"] == "revoked"
    with pytest.raises(PermissionError, match="revoked"):
        bindings.resolve(original["reference"])


def test_canvas_redaction_removes_secret_keys_and_secret_shaped_values():
    clean = AionFlowModelBindings.redact_for_canvas(
        {
            "api_key": "secret",
            "endpoint_binding_ref": "vault://model/private",
            "nested": {"note": "Bearer something-sensitive"},
            "safe": "model-name",
        }
    )
    assert clean["api_key"] == "[REDACTED]"
    assert clean["endpoint_binding_ref"] == "vault://model/private"
    assert clean["nested"]["note"] == "[REDACTED]"
    assert clean["safe"] == "model-name"


def test_health_test_is_bounded_and_does_not_return_endpoint_response():
    class Registry:
        def health(self, adapter_id, timeout_seconds):
            assert adapter_id == "private"
            assert timeout_seconds == 5.0
            return {
                "healthy": True,
                "status": 200,
                "latency_ms": 12,
                "models": [{"id": "private-name"}],
                "authorization": "Bearer secret",
            }

    result = AionFlowModelBindings.bounded_connectivity_test(Registry(), "private", timeout_seconds=99)
    assert result["healthy"] is True
    assert result["response_body_exposed"] is False
    assert "models" not in result
    assert "authorization" not in result


def test_empty_or_oversized_binding_secrets_fail_closed(tmp_path):
    bindings = AionFlowModelBindings(tmp_path / "bindings")
    with pytest.raises(ValueError, match="secret_required"):
        bindings.create(binding_id="empty", provider="private", secret="  ")
    with pytest.raises(ValueError, match="secret_too_large"):
        bindings.create(binding_id="large", provider="private", secret="x" * 65537)
