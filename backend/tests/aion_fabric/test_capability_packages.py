from __future__ import annotations

import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.capability_packages import CapabilityPackageAuthority
from backend.modules.aion_fabric.identity import DeviceIdentity


def identity():
    return DeviceIdentity(Ed25519PrivateKey.generate())


def payload(artifact, *, package_id="sales-adviser", publisher_class="tessaris"):
    raw = artifact.read_bytes()
    return {
        "package_id": package_id,
        "version": "1.0.0",
        "name": "Sales Adviser",
        "department": "sales",
        "industry": "general",
        "artifact": {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
        "permissions": {
            "network_hosts": ["crm.customer.example"],
            "file_roots": [str(artifact.parent / "allowed")],
            "identity_scopes": ["sales.read"],
            "tools": ["crm.search"],
            "execution_actions": ["crm.prepare_draft"],
        },
        "limits": {"maximum_authorizations": 3, "maximum_seconds": 30, "maximum_cost": 0.10},
        "components": {"prompt": "p2", "procedure": "r1", "tools": "t1", "policy": "g1"},
        "component_versions": {"prompt": ["p1", "p2"], "procedure": ["r1"], "tools": ["t1"], "policy": ["g1", "g2"]},
        "publishing": {"publisher_class": publisher_class, "curated": publisher_class == "tessaris", "commercial_terms": "included" if publisher_class != "third_party" else "20_percent_revenue_share"},
        "contains_customer_brain": False,
        "contains_customer_data": False,
    }


def installed(tmp_path, *, publisher_class="tessaris"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    publisher = identity()
    artifact = tmp_path / "package.zip"
    artifact.write_bytes(b"bounded capability package")
    (tmp_path / "allowed").mkdir()
    authority = CapabilityPackageAuthority(tmp_path / "registry", trusted_publishers=[publisher.public_key_b64])
    manifest = authority.sign_manifest(payload(artifact, publisher_class=publisher_class), publisher)
    ref = authority.package_ref(manifest)
    authority.install(manifest, artifact)
    return authority, publisher, artifact, manifest, ref


def qualify(authority, ref):
    for kind in ("dry_run", "adversarial_permission", "outcome"):
        authority.record_test(ref, kind=kind, passed=True, evidence={"suite": f"{kind}-v1"})


def test_manifest_signature_trust_integrity_and_immutability(tmp_path):
    authority, publisher, artifact, manifest, ref = installed(tmp_path)
    assert authority.record(ref)["status"] == "installed_unqualified"
    changed = dict(manifest)
    changed["name"] = "Tampered"
    with pytest.raises(ValueError, match="hash_mismatch"):
        authority.install(changed, artifact)
    stranger = identity()
    untrusted = authority.sign_manifest(payload(artifact, package_id="unknown"), stranger)
    with pytest.raises(PermissionError, match="not_trusted"):
        authority.install(untrusted, artifact)
    artifact.write_bytes(b"changed bytes")
    with pytest.raises(ValueError, match="integrity_mismatch"):
        authority.install(manifest, artifact)


def test_package_cannot_copy_customer_brain_or_data(tmp_path):
    publisher = identity()
    artifact = tmp_path / "bad.zip"
    artifact.write_bytes(b"bad")
    value = payload(artifact)
    value["contains_customer_brain"] = True
    manifest = CapabilityPackageAuthority.sign_manifest(value, publisher)
    authority = CapabilityPackageAuthority(tmp_path / "registry", trusted_publishers=[publisher.public_key_b64])
    with pytest.raises(PermissionError, match="must_not_copy"):
        authority.install(manifest, artifact)


def test_activation_requires_all_three_tests_and_human_accountability(tmp_path):
    authority, _publisher, _artifact, _manifest, ref = installed(tmp_path)
    authority.record_test(ref, kind="dry_run", passed=True, evidence={})
    authority.record_test(ref, kind="adversarial_permission", passed=True, evidence={})
    with pytest.raises(PermissionError, match="qualification_incomplete"):
        authority.activate(ref, accountable_owner="owner-1", approval_receipt="approval-1")
    authority.record_test(ref, kind="outcome", passed=True, evidence={})
    with pytest.raises(PermissionError, match="human_owner"):
        authority.activate(ref, accountable_owner="", approval_receipt="approval-1")
    activation = authority.activate(ref, accountable_owner="owner-1", approval_receipt="approval-1")
    assert activation["accountable_owner"] == "owner-1"
    assert "approval-1" not in json.dumps(activation)


def test_undeclared_network_file_identity_tool_and_execution_are_denied(tmp_path):
    authority, _publisher, _artifact, _manifest, ref = installed(tmp_path)
    qualify(authority, ref)
    authority.activate(ref, accountable_owner="owner-1", approval_receipt="approval-1")
    assert authority.authorize(ref, kind="tool", target="crm.search")["accountable_owner"] == "owner-1"
    assert authority.authorize(ref, kind="network", target="crm.customer.example")["kind"] == "network"
    with pytest.raises(PermissionError, match="undeclared_network"):
        authority.authorize(ref, kind="network", target="attacker.example")
    with pytest.raises(PermissionError, match="undeclared_file"):
        authority.authorize(ref, kind="file", target=str(tmp_path / "outside" / "secret"))
    with pytest.raises(PermissionError, match="raw_execution"):
        authority.authorize(ref, kind="execution", target="crm.prepare_draft", action="/bin/sh")


def test_authorization_budget_is_bounded(tmp_path):
    authority, _publisher, _artifact, _manifest, ref = installed(tmp_path)
    qualify(authority, ref)
    authority.activate(ref, accountable_owner="owner-1", approval_receipt="approval-1")
    for _ in range(3):
        authority.authorize(ref, kind="tool", target="crm.search")
    with pytest.raises(PermissionError, match="limit_reached"):
        authority.authorize(ref, kind="tool", target="crm.search")

def test_prompt_procedure_tool_and_policy_versions_change_independently(tmp_path):
    authority, _publisher, _artifact, _manifest, ref = installed(tmp_path)
    changed = authority.select_component(ref, component="prompt", version="p1")
    assert changed == {"component": "prompt", "previous": "p2", "selected": "p1"}
    record = authority.record(ref)
    assert record["active_components"]["procedure"] == "r1"
    assert record["active_components"]["tools"] == "t1"
    assert record["active_components"]["policy"] == "g1"
    with pytest.raises(PermissionError, match="not_declared"):
        authority.select_component(ref, component="policy", version="g99")


def test_curated_and_third_party_catalogue_has_commercial_controls(tmp_path):
    authority, _publisher, _artifact, _manifest, ref = installed(tmp_path, publisher_class="third_party")
    catalogue = authority.catalogue()
    assert catalogue["customer_brain_content_exposed"] is False
    entry = catalogue["entries"][0]
    assert entry["package_ref"] == ref
    assert entry["publisher_class"] == "third_party"
    assert entry["commercial_terms"] == "20_percent_revenue_share"
    assert entry["curated"] is False


def test_revoke_and_remove_end_authority_without_touching_external_state(tmp_path):
    external = tmp_path / "business-map.json"
    external.write_text('{"facts":4}', encoding="utf-8")
    before = hashlib.sha256(external.read_bytes()).hexdigest()
    authority, _publisher, _artifact, _manifest, ref = installed(tmp_path / "package-root")
    qualify(authority, ref)
    authority.activate(ref, accountable_owner="owner-1", approval_receipt="approval-1")
    authority.revoke(ref, reason="publisher security notice")
    with pytest.raises(PermissionError, match="active_capability"):
        authority.authorize(ref, kind="tool", target="crm.search")
    assert authority.remove(ref)["evidence_retained"] is True
    assert authority.record(ref)["status"] == "removed"
    assert hashlib.sha256(external.read_bytes()).hexdigest() == before
