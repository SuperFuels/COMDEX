from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.aion_flow_harness_context import AionFlowHarnessAuthority
from backend.modules.aion_fabric.identity import DeviceIdentity


def identity():
    return DeviceIdentity(Ed25519PrivateKey.generate())


def manifest(issuer, harness_id="sales-analysis", version="1"):
    return AionFlowHarnessAuthority.sign_manifest({
        "harness_id": harness_id,
        "version": version,
        "instructions": "Analyse supplied evidence; do not invent facts.",
        "input_schema": {"required": ["sales"]},
        "output_schema": {"required": ["findings", "uncertainty"]},
        "examples": [{"input": {"sales": []}, "output": {"findings": [], "uncertainty": "high"}}],
        "declared_tools": [{"tool_id": "calculator", "network_hosts": [], "file_roots": [], "actions": ["calculate"]}],
        "domain_pack": {"department": "sales", "industry": "general", "use_case": "variance_analysis"},
    }, issuer)


def test_signed_harness_is_immutable_and_independent_from_model(tmp_path):
    issuer = identity()
    authority = AionFlowHarnessAuthority(tmp_path, trusted_issuers=[issuer.public_key_b64])
    signed = manifest(issuer)
    record = authority.register(signed)
    reference = authority.harness_ref(signed)
    assert record["manifest_hash"] == signed["manifest_hash"]
    changed = manifest(issuer)
    changed["instructions"] = "changed"
    changed = authority.sign_manifest(changed, issuer)
    with pytest.raises(PermissionError, match="immutable"):
        authority.register(changed)
    forbidden = manifest(issuer, harness_id="coupled")
    forbidden["model_id"] = "provider-model"
    forbidden = authority.sign_manifest(forbidden, issuer)
    with pytest.raises(PermissionError, match="independent"):
        authority.register(forbidden)
    assert authority.record(reference)["manifest"].get("model_id") is None


def test_harness_versions_compare_select_and_rollback_independently(tmp_path):
    issuer = identity()
    authority = AionFlowHarnessAuthority(tmp_path, trusted_issuers=[issuer.public_key_b64])
    first = manifest(issuer, version="1")
    second = manifest(issuer, version="2")
    second["instructions"] = "Analyse, quantify and preserve dissent."
    second = authority.sign_manifest(second, issuer)
    for item in (first, second):
        authority.register(item)
    ref1, ref2 = authority.harness_ref(first), authority.harness_ref(second)
    authority.select(route_id="sales", harness_ref=ref1)
    assert authority.select(route_id="sales", harness_ref=ref2)["active"] == ref2
    assert "instructions" in authority.compare(ref1, ref2)["changed_fields"]
    assert authority.rollback(route_id="sales")["active"] == ref1


def test_minimum_context_enforces_identity_scope_redaction_summary_and_preflight(tmp_path):
    authority = AionFlowHarnessAuthority(tmp_path, trusted_issuers=[])
    result = authority.assemble_context(
        identity={"person_id": "p1", "organisation_id": "o1", "workspace_id": "w1", "role": "analyst", "space_id": "business"},
        purpose="Explain sales variance",
        memory={"preferences": {"tone": "concise"}},
        business_map={"sales": {"revenue": 100, "customers": ["A", "B"]}, "payroll": {"salaries": [1]}},
        include=["memory.preferences.tone", "business_map.sales.revenue", "business_map.sales.customers"],
        redact=["business_map.sales.revenue"],
        summarize=["business_map.sales.customers"],
        permitted_paths=["memory.preferences", "business_map.sales"],
        downstream=[{"node_id": "private-model", "destination": "customer_vpc", "fields": ["business_map.sales.revenue"], "data_classes": ["business_internal"], "encrypted": True}],
    )
    fields = result["context"]["fields"]
    assert fields["business_map.sales.revenue"].startswith("[REDACTED")
    assert fields["business_map.sales.customers"] == {"type": "list", "item_count": 2}
    assert result["disclosure_preflight"][0]["fields"] == ["business_map.sales.revenue"]
    with pytest.raises(PermissionError, match="path_denied"):
        authority.assemble_context(
            identity={"person_id": "p1", "organisation_id": "o1", "workspace_id": "w1", "role": "analyst"},
            purpose="read payroll", memory={}, business_map={"payroll": {"salaries": []}},
            include=["business_map.payroll.salaries"], permitted_paths=["business_map.sales"],
        )


def test_harness_sandbox_rejects_undeclared_tool_and_access(tmp_path):
    issuer = identity()
    authority = AionFlowHarnessAuthority(tmp_path, trusted_issuers=[issuer.public_key_b64])
    signed = manifest(issuer)
    authority.register(signed)
    reference = authority.harness_ref(signed)
    assert authority.authorize_tool(reference, tool_id="calculator", access={"actions": ["calculate"]})["tool_id"] == "calculator"
    with pytest.raises(PermissionError, match="undeclared"):
        authority.authorize_tool(reference, tool_id="browser", access={})
    with pytest.raises(PermissionError, match="network_hosts_denied"):
        authority.authorize_tool(reference, tool_id="calculator", access={"network_hosts": ["example.com"]})
