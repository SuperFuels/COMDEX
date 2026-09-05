from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_business.runtime.aion_flow_evidence_engine import AionFlowEvidenceEngine


def row(source_id="source-1", content="Revenue was 100.", age=0, quality=0.9):
    return {
        "source_id": source_id, "uri": "customer://sales/report", "title": "Sales report",
        "content": content, "observed_at": (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat(),
        "quality": quality,
    }


def test_authorized_business_and_public_retrievers_preserve_provenance_and_separation():
    engine = AionFlowEvidenceEngine()
    engine.register_retriever("crm", source_kind="crm", retrieve=lambda query: [row()], allowed_purposes=["analysis"])
    result = engine.retrieve("crm", query="revenue", purpose="analysis", cache_seconds=60)
    document = result["documents"][0]
    assert document["content_hash"]
    assert document["source_kind"] == "crm"
    assert result["interpretation"] is None
    assert engine.retrieve("crm", query="revenue", purpose="analysis", cache_seconds=60)["cache"] == "hit"
    with pytest.raises(PermissionError, match="purpose_not_allowed"):
        engine.retrieve("crm", query="revenue", purpose="marketing")


def test_evidence_pack_maps_claims_and_fails_closed_on_missing_stale_or_weak_sources():
    engine = AionFlowEvidenceEngine()
    engine.register_retriever("db", source_kind="database", retrieve=lambda query: [row(age=100, quality=0.4)], allowed_purposes=["analysis"])
    retrieval = engine.retrieve("db", query="revenue", purpose="analysis")
    pack = engine.build_pack([retrieval], claims=[{"claim": "Revenue was 100", "source_ids": ["source-1"], "verdict": "true", "confidence": 0.8}], maximum_age_seconds=10, minimum_quality=0.7)
    assert pack["status"] == "unresolved"
    assert pack["downstream_execution_allowed"] is False
    assert any("stale" in item for item in pack["errors"])
    assert any("quality" in item for item in pack["errors"])


def test_contradiction_detection_preserves_uncertainty():
    engine = AionFlowEvidenceEngine()
    engine.register_retriever("file", source_kind="file", retrieve=lambda query: [row("a"), row("b")], allowed_purposes=["review"])
    retrieval = engine.retrieve("file", query="claim", purpose="review")
    pack = engine.build_pack([retrieval], claims=[
        {"claim": "The target was met", "source_ids": ["a"], "verdict": "true", "confidence": 0.8},
        {"claim": "The target was met", "source_ids": ["b"], "verdict": "false", "confidence": 0.8},
    ])
    assert pack["contradictions"] == ["the target was met"]
    assert pack["status"] == "unresolved"


def test_deterministic_schema_calculation_policy_and_business_validators():
    engine = AionFlowEvidenceEngine()
    assert engine.validate("json_schema", {"answer": 3}, {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "number"}}})["passed"] is True
    assert engine.validate("calculation", 10.1, {"expected": 10, "tolerance": 0.2})["passed"] is True
    engine.register_validator("business_rule", lambda value, rule: (value <= rule["maximum"], [] if value <= rule["maximum"] else ["maximum_exceeded"]))
    assert engine.validate("business_rule", 12, {"maximum": 10})["passed"] is False


def test_revocation_propagates_and_source_is_not_reacquired():
    engine = AionFlowEvidenceEngine()
    engine.register_retriever("accounting", source_kind="accounting", retrieve=lambda query: [row()], allowed_purposes=["audit"])
    first = engine.retrieve("accounting", query="revenue", purpose="audit")
    assert first["documents"]
    engine.revoke_source("source-1", reason="superseded")
    assert first["documents"][0]["status"] == "revoked"
    assert engine.retrieve("accounting", query="new", purpose="audit")["documents"] == []


def test_required_evidence_absence_fails_closed():
    engine = AionFlowEvidenceEngine()
    pack = engine.build_pack([], claims=[{"claim": "Unsupported", "source_ids": [], "confidence": 0.9}], required_evidence=True)
    assert pack["downstream_execution_allowed"] is False
    assert "claim_evidence_required" in pack["errors"]
