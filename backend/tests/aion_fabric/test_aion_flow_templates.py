from __future__ import annotations

import copy

import pytest

from backend.modules.aion_business.runtime.aion_flow_templates import AionFlowTemplateLibrary


def test_builtin_template_catalogue_is_signed_and_state_free(tmp_path):
    library = AionFlowTemplateLibrary(tmp_path)
    catalogue = library.list()
    assert len(catalogue["templates"]) == 6
    assert catalogue["third_party_publishing_enabled"] is False
    for item in catalogue["templates"]:
        inspected = library.inspect(item["template_ref"])
        assert inspected["signature_valid"] is True
        assert inspected["dependencies"]["compatible"] is True
        assert inspected["customer_bindings_in_package"] is False
        assert "vault://" not in str(inspected["manifest"]["graph"])


def test_install_keeps_bindings_opaque_and_grants_no_authority(tmp_path):
    library = AionFlowTemplateLibrary(tmp_path)
    installed = library.install(
        "gemini-evidence-analysis@1.0.0",
        organisation_id="org-1",
        bindings={"model_provider": "vault://model/gemini-primary"},
        actor_role="owner",
    )
    assert installed["authority_granted"] is False
    assert installed["status"] == "installed_unapproved"
    assert library.list_installations(organisation_id="org-1")["installations"][0]["bindings"] == {
        "model_provider": "vault://model/gemini-primary"
    }

    with pytest.raises(ValueError, match="opaque"):
        library.install(
            "gemini-evidence-analysis@1.0.0",
            organisation_id="org-1",
            bindings={"model_provider": "plain-api-key"},
            actor_role="owner",
        )


def test_private_library_roles_version_pin_rollback_and_remove(tmp_path):
    library = AionFlowTemplateLibrary(tmp_path)
    original = copy.deepcopy(library.inspect("local-first-research@1.0.0")["manifest"])
    payload = {key: value for key, value in original.items() if key not in {"signature", "manifest_hash", "publisher_public_key", "schema_version"}}
    payload.update({"template_id": "org-research", "version": "1.0.0"})
    first = library.publish_private(organisation_id="org-1", payload=payload, actor_role="workflow_publisher")
    assert first["manifest"]["publisher_class"] == "customer_private"
    installed = library.install("org-research@1.0.0", organisation_id="org-1", bindings={}, actor_role="admin")

    payload["version"] = "1.1.0"
    library.publish_private(organisation_id="org-1", payload=payload, actor_role="workflow_publisher")
    pinned = library.pin(installed["installation_id"], template_ref="org-research@1.1.0", actor_role="admin")
    assert pinned["active_template_ref"] == "org-research@1.1.0"
    assert library.rollback(installed["installation_id"], actor_role="owner")["active_template_ref"] == "org-research@1.0.0"
    assert library.remove(installed["installation_id"], actor_role="owner")["status"] == "removed"


def test_quarantined_or_revoked_templates_cannot_install(tmp_path):
    library = AionFlowTemplateLibrary(tmp_path)
    library.lifecycle("boardroom-decision-analysis@1.0.0", action="quarantine", reason="review", actor_role="admin")
    with pytest.raises(PermissionError, match="not_installable"):
        library.install("boardroom-decision-analysis@1.0.0", organisation_id="org", bindings={}, actor_role="owner")


@pytest.mark.parametrize("secret_key", ["api_key", "password", "access_token", "private_key", "authorization_header"])
def test_private_template_rejects_nested_secret_shaped_fields(tmp_path, secret_key):
    library = AionFlowTemplateLibrary(tmp_path)
    original = copy.deepcopy(library.inspect("local-first-research@1.0.0")["manifest"])
    payload = {key: value for key, value in original.items() if key not in {"signature", "manifest_hash", "publisher_public_key", "schema_version"}}
    payload.update({"template_id": f"secret-test-{secret_key.replace('_', '-')}", "version": "1.0.0"})
    payload["graph"]["nodes"][0]["config"] = {secret_key: "must-never-be-signed"}
    with pytest.raises(ValueError, match="secret_shaped"):
        library.publish_private(organisation_id="org-1", payload=payload, actor_role="owner")
    library.lifecycle("boardroom-decision-analysis@1.0.0", action="restore", reason="review complete", actor_role="admin")
    library.lifecycle("boardroom-decision-analysis@1.0.0", action="revoke", reason="superseded", actor_role="admin")
    with pytest.raises(PermissionError, match="not_installable"):
        library.install("boardroom-decision-analysis@1.0.0", organisation_id="org", bindings={}, actor_role="owner")
