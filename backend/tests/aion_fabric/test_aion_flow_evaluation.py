from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.aion_flow_evaluation import AionFlowEvaluationService


def graph():
    return {
        "workflow_id": "research-flow",
        "nodes": [
            {"id": "brain", "type": "brain", "config": {"module_id": "intelligence.aion_admission"}},
            {"id": "model", "type": "model", "config": {"module_id": "intelligence.model_local", "intelligence_settings": {"model_manifest_id": "local-v1"}}},
            {"id": "receipt", "type": "verification", "config": {"module_id": "intelligence.verify_receipt"}},
        ],
        "edges": [{"source": "brain", "target": "model"}, {"source": "model", "target": "receipt"}],
    }


def result(item, **metrics):
    return {
        "evidence_pack_hash": item["evidence_pack_hash"],
        "verified_outcome": True,
        "receipt_ref": "receipt://verified",
        "provider_fingerprint": "provider-v1",
        "metrics": metrics,
    }


def test_duplicate_and_swap_preserves_champion_and_versioned_evidence(tmp_path):
    service = AionFlowEvaluationService(tmp_path)
    item = service.create(graph=graph(), node_id="model", challenger_value="local-v2", evidence_pack={"id": "pack-1", "claims": ["verified"]}, minimum_samples=1)
    assert item["variants"]["champion"]["graph"]["nodes"][1]["config"]["intelligence_settings"]["model_manifest_id"] == "local-v1"
    assert item["variants"]["challenger"]["graph"]["nodes"][1]["config"]["intelligence_settings"]["model_manifest_id"] == "local-v2"
    assert item["variants"]["champion"]["graph_hash"] != item["variants"]["challenger"]["graph_hash"]
    assert item["traffic"]["bounded"] is True


def test_only_same_pack_verified_outcomes_or_corrections_influence_learning(tmp_path):
    service = AionFlowEvaluationService(tmp_path)
    item = service.create(graph=graph(), node_id="model", challenger_value="local-v2", evidence_pack={"id": "pack-1"}, minimum_samples=1)
    with pytest.raises(ValueError, match="same_versioned"):
        service.record(item["experiment_id"], variant="champion", result={"evidence_pack_hash": "wrong", "metrics": {}})
    ignored = service.record(item["experiment_id"], variant="champion", result={"evidence_pack_hash": item["evidence_pack_hash"], "metrics": {"quality": 1}})
    assert ignored["learning"]["ignored_unverified_count"] == 1
    assert ignored["comparison"]["sample_counts"]["champion"] == 0


def test_metrics_promotion_drift_and_reversal_are_inspectable(tmp_path):
    service = AionFlowEvaluationService(tmp_path)
    item = service.create(graph=graph(), node_id="model", challenger_value="local-v2", evidence_pack={"id": "pack-1"}, minimum_samples=1)
    item = service.record(item["experiment_id"], variant="champion", result=result(item, quality=.7, correctness=.8, evidence_coverage=.8, latency_ms=100, cost=.2, energy_wh=.1))
    item = service.record(item["experiment_id"], variant="challenger", result=result(item, quality=.9, correctness=.9, evidence_coverage=.9, latency_ms=80, cost=.1, energy_wh=.08))
    assert item["comparison"]["challenger_eligible"] is True
    promoted = service.promote(item["experiment_id"], actor_id="owner", reason="Better verified outcomes")
    assert promoted["routing"]["active"] == "challenger"
    assert promoted["routing"]["history"][0]["comparison_hash"]
    reversed_item = service.reverse(item["experiment_id"], actor_id="owner", reason="Provider incident")
    assert reversed_item["routing"]["active"] == "champion"
    assert len(reversed_item["routing"]["history"]) == 2
    assert "private-test-key" not in json.dumps(reversed_item)


def test_regression_blocks_promotion(tmp_path):
    service = AionFlowEvaluationService(tmp_path)
    item = service.create(graph=graph(), node_id="model", challenger_value="local-v2", evidence_pack={"id": "pack-1"}, minimum_samples=1)
    item = service.record(item["experiment_id"], variant="champion", result=result(item, quality=.8, correctness=.9, evidence_coverage=.9))
    item = service.record(item["experiment_id"], variant="challenger", result=result(item, quality=.9, correctness=.5, evidence_coverage=.9))
    assert item["drift"]["detected"] is True
    with pytest.raises(PermissionError, match="not_eligible"):
        service.promote(item["experiment_id"], actor_id="owner", reason="unsafe")


def test_paired_simulation_uses_identical_pack_and_never_teaches_routing(tmp_path):
    service = AionFlowEvaluationService(tmp_path)
    item = service.create(graph=graph(), node_id="model", challenger_value="local-v2", evidence_pack={"id": "pack-1"}, minimum_samples=1)
    observed = []

    def runner(variant_graph, evidence_pack):
        observed.append((variant_graph, evidence_pack))
        return {"ok": True, "phase": "prepared", "metrics": {"quality": 1, "correctness": 1}}

    paired = service.run_same_pack(item["experiment_id"], runner=runner)
    assert len(observed) == 2
    assert observed[0][1] == observed[1][1]
    assert paired["simulations"][0]["same_pack_verified"] is True
    assert paired["simulations"][0]["external_writes"] == 0
    assert paired["comparison"]["sample_counts"] == {"champion": 0, "challenger": 0}
