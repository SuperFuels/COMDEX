from __future__ import annotations

import json
import zipfile

import pytest

from backend.modules.aion_business.runtime.capability_packages import CapabilityPackageAuthority
from scripts.build_sales_lead_response_capability_pack import build


def test_pack_is_deterministic_and_contains_only_declared_components(tmp_path):
    first = build(tmp_path / "one")
    second = build(tmp_path / "two")
    assert first["artifact"].read_bytes() == second["artifact"].read_bytes()
    with zipfile.ZipFile(first["artifact"]) as archive:
        assert sorted(archive.namelist()) == sorted(("prompt/v1.md", "procedure/v1.json", "tools/v1.json", "policy/v1.json"))
        assert "exact_content_approval" in archive.read("policy/v1.json").decode()


def test_signed_pack_installs_but_cannot_activate_before_qualification(tmp_path):
    built = build(tmp_path / "built")
    manifest = json.loads(built["manifest"].read_text())
    authority = CapabilityPackageAuthority(tmp_path / "authority", trusted_publishers=[built["publisher_public_key"]])
    installed = authority.install(manifest, built["artifact"])
    assert installed["status"] == "installed_unqualified"
    with pytest.raises(PermissionError, match="qualification_incomplete"):
        authority.activate("aion.sales.lead_response@1.0.0", accountable_owner="sales.owner", approval_receipt="approval.1")


def test_pack_carries_no_customer_state_credentials_or_unbounded_network(tmp_path):
    built = build(tmp_path / "built")
    manifest = json.loads(built["manifest"].read_text())
    assert manifest["contains_customer_brain"] is False
    assert manifest["contains_customer_data"] is False
    assert manifest["permissions"]["network_hosts"] == []
    assert manifest["requires_authorized_connector"] is True
    assert manifest["live_delivery_qualified"] is False
    serialized = built["artifact"].read_bytes().lower()
    for marker in (b"api_key", b"password", b"bearer ", b"customer@example"):
        assert marker not in serialized


def test_pack_qualifies_under_three_distinct_gates_and_stays_least_authority(tmp_path):
    built = build(tmp_path / "built")
    manifest = json.loads(built["manifest"].read_text())
    authority = CapabilityPackageAuthority(tmp_path / "authority", trusted_publishers=[built["publisher_public_key"]])
    authority.install(manifest, built["artifact"])
    ref = "aion.sales.lead_response@1.0.0"
    for kind in ("dry_run", "adversarial_permission", "outcome"):
        authority.record_test(ref, kind=kind, passed=True, evidence={"suite": f"sales-{kind}-v1", "synthetic": True})
    authority.activate(ref, accountable_owner="sales.owner", approval_receipt="approval.1")
    assert authority.authorize(ref, kind="tool", target="email.prepare_draft")["kind"] == "tool"
    with pytest.raises(PermissionError, match="undeclared_network"):
        authority.authorize(ref, kind="network", target="mail.provider.example")
