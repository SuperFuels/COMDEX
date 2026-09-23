import json
from pathlib import Path

import pytest

from backend.modules.connectors.tool_manifest import ToolManifestError, validate_tool_manifest


TEMPLATE = (
    Path(__file__).parents[2]
    / "modules"
    / "connectors"
    / "templates"
    / "provider_tool_manifest.template.json"
)


def _manifest():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def test_provider_template_is_a_valid_governed_manifest():
    result = validate_tool_manifest(_manifest())

    assert result["valid"] is True
    assert result["tool_id"] == "example_provider"
    assert result["action_count"] == 2
    assert len(result["manifest_sha256"]) == 64


def test_external_write_requires_receipt_idempotency_and_fail_closed():
    manifest = _manifest()
    action = manifest["actions"][1]
    action["receipt"]["required"] = False
    action["execution"]["idempotency"] = "not_applicable"
    action["failure"]["fail_closed"] = False

    with pytest.raises(ToolManifestError) as error:
        validate_tool_manifest(manifest)

    message = str(error.value)
    assert "external_write_requires_receipt" in message
    assert "external_write_requires_idempotency" in message
    assert "external_write_must_fail_closed" in message


def test_manifest_rejects_embedded_credentials():
    manifest = _manifest()
    manifest["connection"]["api_key"] = "should-never-be-here"

    with pytest.raises(ToolManifestError, match="secret_must_live_in_vault"):
        validate_tool_manifest(manifest)


def test_financial_action_requires_currency_and_amount_limit_contract():
    manifest = _manifest()
    action = manifest["actions"][1]
    action["kind"] = "financial"
    action["risk"]["financial"] = True

    with pytest.raises(ToolManifestError) as error:
        validate_tool_manifest(manifest)

    assert "financial_limit_required" in str(error.value)
    assert "financial_currency_required" in str(error.value)

