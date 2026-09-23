from __future__ import annotations

import copy

import pytest

from backend.modules.aion_business.contracts.sovereign_brain import (
    CANONICAL_STORE_KINDS,
    assert_provider_adapter_boundary,
    build_brain_export_manifest,
    build_brain_identity,
    build_business_map,
    build_intelligence_route_receipt,
    published_schemas,
)
from backend.modules.aion_business.runtime.sovereign_flow_compiler import (
    SovereignFlowCompiler,
    reference_flow,
)
from backend.modules.aion_business.runtime.sovereign_brain_boundary import SovereignBrainBoundary


def test_sovereign_contracts_do_not_bind_customer_state_to_provider():
    identity = build_brain_identity(
        brain_id="brain_customer_1", owner_id="owner_1", public_key_fingerprint="sha256:test"
    )
    assert identity["provider_bindings"] == []
    assert tuple(identity["canonical_stores"]) == CANONICAL_STORE_KINDS
    assert set(published_schemas()) == {
        "brain_identity", "brain_export", "business_map", "intelligence_route_receipt"
    }


def test_provider_cannot_claim_canonical_memory_or_authority():
    assert_provider_adapter_boundary({"provider": "replaceable", "authorities": []})
    with pytest.raises(ValueError, match="provider_authority_forbidden"):
        assert_provider_adapter_boundary(
            {"provider": "replaceable", "authorities": ["write_canonical_memory"]}
        )


def test_business_map_requires_provenance_and_confidence():
    result = build_business_map(
        brain_id="brain_customer_1",
        nodes=[{"id": "team.sales", "source": "owner_interview", "confidence": 0.9}],
        edges=[],
    )
    assert result["nodes"][0]["review_state"] == "proposed"
    assert len(result["content_hash"]) == 64
    with pytest.raises(ValueError, match="business_map_source_required"):
        build_business_map(brain_id="brain_customer_1", nodes=[{"id": "x", "confidence": 1}], edges=[])


def test_route_receipt_hashes_content_instead_of_retaining_it():
    receipt = build_intelligence_route_receipt(
        brain_id="brain_customer_1",
        request={"prompt": "private business question"},
        route={"provider": "local", "model": "qualified-model"},
        result={"answer": "private result"},
        disclosure={"destination": "local", "fields": []},
        budget={"seconds": 30, "cost": 0},
    )
    assert "private business question" not in str(receipt)
    assert "private result" not in str(receipt)
    assert receipt["raw_prompt_retained"] is False


def test_complete_brain_export_does_not_include_provider_credentials():
    identity = build_brain_identity(
        brain_id="brain_customer_1", owner_id="owner_1", public_key_fingerprint="sha256:test"
    )
    stores = {name: {"schema_version": "v1", "records": []} for name in CANONICAL_STORE_KINDS}
    manifest = build_brain_export_manifest(brain_identity=identity, stores=stores)
    assert manifest["provider_credentials_included"] is False
    assert set(manifest["stores"]) == set(CANONICAL_STORE_KINDS)


def test_brain_boots_and_restarts_without_cloud_keys_or_provider_state(tmp_path):
    first = SovereignBrainBoundary.bootstrap(
        tmp_path / "brain",
        brain_id="brain_customer_1",
        owner_id="owner_1",
        public_key_fingerprint="sha256:test",
    )
    assert first.status()["ok"] is True
    assert first.status()["provider_keys_required"] is False
    restarted = SovereignBrainBoundary(tmp_path / "brain")
    assert restarted.status() == first.status()


def test_reference_flow_is_enclosed_by_aion_and_does_not_execute():
    result = SovereignFlowCompiler().compile(reference_flow())
    assert result.ok is True
    assert result.manifest["execution_state"] == "compiled_not_executed"
    assert result.manifest["aion_boundary"] == {"ingress": "admit", "receipt": "receipt"}


def test_model_swap_preserves_flow_and_customer_state_contract():
    first = reference_flow()
    second = copy.deepcopy(first)
    model = next(node for node in second["nodes"] if node["id"] == "specialist_a")
    model.update({"provider": "different-provider", "model": "replacement-model"})
    before = SovereignFlowCompiler().compile(first)
    after = SovereignFlowCompiler().compile(second)
    assert before.ok and after.ok
    assert before.manifest["aion_boundary"] == after.manifest["aion_boundary"]
    assert before.manifest["manifest_hash"] != after.manifest["manifest_hash"]


def test_flow_rejects_model_authority_unbounded_consensus_and_unguarded_action():
    spec = reference_flow()
    next(node for node in spec["nodes"] if node["id"] == "specialist_a")["authorities"] = [
        "write_canonical_memory"
    ]
    consensus = next(node for node in spec["nodes"] if node["id"] == "compare")
    consensus["max_iterations"] = 0
    spec["edges"] = [edge for edge in spec["edges"] if edge["target"] != "approve"]
    result = SovereignFlowCompiler().compile(spec)
    assert result.ok is False
    assert any("provider_authority_forbidden" in error for error in result.errors)
    assert any("consensus_iteration_limit_required" in error for error in result.errors)
    assert any("node_outside_aion_boundary:approve" in error for error in result.errors)
