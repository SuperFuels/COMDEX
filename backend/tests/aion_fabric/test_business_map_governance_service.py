from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.modules.aion_business.api import business_twin_data_api as business_api
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.business_map_governance_service import BusinessMapGovernanceService
from backend.modules.aion_business.runtime.sovereign_boardroom_bridge import SovereignBoardroomBridge
from backend.modules.aion_business.runtime.sovereign_brain_setup import SovereignBrainSetup
from backend.modules.aion_business.contracts.business_containers import BusinessStructureContainer


def _service(tmp_path):
    setup = SovereignBrainSetup(tmp_path)
    status = setup.initialize(owner_display_name="Owner")
    bridge = SovereignBoardroomBridge(tmp_path)
    bridge.create_empty_workspace("company", owner_id=status["owner_id"])
    repository = BusinessContainerRepository(tmp_path / "AION_BUSINESS" / "business_containers")
    return BusinessMapGovernanceService(repository)


def test_proposed_fact_requires_provenance_confidence_and_owner_review(tmp_path):
    service = _service(tmp_path)
    proposal = service.propose_fact(
        "company", field="offer", value="Repairs", source_ref="owner:interview:1",
        confidence=0.9, proposed_by="owner", review_owner_id="owner", expected_revision=0,
    )
    assert proposal["fact"]["review_state"] == "proposed"
    assert service.queues("company")["counts"]["proposed"] == 1
    reviewed = service.review_fact(
        "company", proposal["fact"]["fact_id"], action="approve", actor_id="owner",
        expected_revision=1,
    )
    assert reviewed["fact"]["verification_status"] == "owner_attested"
    assert service.queues("company")["counts"]["proposed"] == 0


def test_correction_preserves_hash_history_and_delete_requires_exact_confirmation(tmp_path):
    service = _service(tmp_path)
    proposal = service.propose_fact(
        "company", field="currency", value="USD", source_ref="owner:interview:2",
        confidence=1, proposed_by="owner",
    )
    fact_id = proposal["fact"]["fact_id"]
    corrected = service.review_fact(
        "company", fact_id, action="correct", actor_id="owner", corrected_value="EUR",
        expected_revision=1, reason="Business trades in Spain",
    )
    assert corrected["fact"]["value"] == "EUR"
    assert corrected["fact"]["revision_history"][0]["value_hash"]
    with pytest.raises(PermissionError, match="delete_confirmation"):
        service.review_fact("company", fact_id, action="delete", actor_id="owner", expected_revision=2)
    deleted = service.review_fact(
        "company", fact_id, action="delete", actor_id="owner", expected_revision=2,
        confirm_delete=True,
    )
    assert deleted["deleted"] is True
    ledger = service.repository.base_dir / "company" / "business_map_governance.jsonl"
    assert len(ledger.read_text().splitlines()) == 3


def test_queues_surface_expired_missing_provenance_and_missing_owner_records(tmp_path):
    service = _service(tmp_path)
    service.propose_fact(
        "company", field="temporary_offer", value="Summer service", source_ref="website:1",
        confidence=0.7, proposed_by="scanner", effective_until="2025-01-01T00:00:00+00:00",
    )
    model = service.repository.load_business_map("company")
    model.facts.append({"fact_id": "legacy", "field": "legacy", "value": "Unknown source"})
    model.unknowns.append({"field": "margin", "reason": "not supplied"})
    model.conflicts.append({"field": "team_size", "values": [2, 3]})
    service.repository.save_model(model)
    queues = service.queues("company", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert queues["counts"]["stale"] == 1
    assert queues["counts"]["missing_provenance"] == 1
    assert queues["counts"]["missing_review_owner"] == 2
    assert queues["counts"]["unknowns"] == 1
    assert queues["counts"]["conflicts"] == 1


def test_export_is_hash_bound_to_the_canonical_boardroom_map(tmp_path):
    service = _service(tmp_path)
    exported = service.export("company")
    assert exported["source_of_truth"] == "boardroom_business_containers"
    assert exported["business_map"]["kind"] == "business_map"
    assert exported["content_hash"]


def test_existing_business_data_api_exposes_governed_fact_lifecycle(tmp_path, monkeypatch):
    service = _service(tmp_path)
    monkeypatch.setattr(business_api, "_business_map_governance", lambda: service)
    proposed = business_api.propose_governed_business_map_fact(
        "company",
        business_api.BusinessMapFactProposalRequest(
            field="service_area", value="Almeria", source_ref="owner:interview:3",
            confidence=0.95, proposed_by="owner", review_owner_id="owner",
        ),
    )
    queues = business_api.get_business_map_governance_queues("company")
    assert queues["counts"]["proposed"] == 1
    reviewed = business_api.review_governed_business_map_fact(
        "company", proposed["fact"]["fact_id"],
        business_api.BusinessMapFactReviewRequest(
            action="approve", actor_id="owner", expected_revision=1,
        ),
    )
    assert reviewed["fact"]["review_state"] == "approved"
    exported = business_api.export_governed_business_map("company")
    assert exported["business_map"]["revision"] == 2


def test_legacy_relationships_are_normalized_and_explicit_structure_links_are_derived(tmp_path):
    service = _service(tmp_path)
    model = service.repository.load_business_map("company")
    model.relationships.append({"from_id": "team:sales", "relationship_type": "owns", "to_id": "service:repairs"})
    service.repository.save_model(model)
    structure = service.repository.load_business_structure("company")
    structure.services = [{"id": "service:repairs", "name": "Repairs"}, {"name": "No invented id"}]
    service.repository.save_model(structure)

    result = service.normalize_legacy_relationships("company", actor_id="owner", expected_revision=0)
    assert result["normalized"] == 1
    assert result["derived"] == 1
    saved = service.repository.load_business_map("company")
    assert len(saved.relationships) == 2
    legacy = saved.relationships[0]
    assert legacy["source_ref"] == "legacy_business_map:relationships:1"
    assert legacy["confidence"] == 0.5
    assert legacy["review_state"] == "proposed"
    derived = saved.relationships[1]
    assert derived["source_ref"] == "business_structure:services:service:repairs"
    assert derived["from_id"] == "business:company"
    assert service.queues("company")["counts"]["relationships_proposed"] == 2

    reviewed = service.review_relationship(
        "company", derived["relationship_id"], action="approve", actor_id="owner", expected_revision=1,
    )
    assert reviewed["relationship"]["verification_status"] == "owner_attested"


def test_owner_can_merge_duplicate_same_field_facts_without_losing_provenance(tmp_path):
    service = _service(tmp_path)
    first = service.propose_fact(
        "company", field="service_area", value="Almeria", source_ref="owner:1", confidence=1,
        proposed_by="owner",
    )["fact"]
    second = service.propose_fact(
        "company", field="service_area", value="Almería", source_ref="document:2", confidence=.8,
        proposed_by="extractor",
    )["fact"]
    merged = service.merge_facts(
        "company", primary_fact_id=first["fact_id"], duplicate_fact_id=second["fact_id"],
        actor_id="owner", expected_revision=2,
    )
    assert merged["fact"]["value"] == "Almeria"
    assert merged["fact"]["verification_status"] == "owner_merged"
    assert "document:2" in merged["fact"]["merged_source_refs"]
    assert len(service.repository.load_business_map("company").facts) == 1
