from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.modules.aion_business.runtime.governed_improvement_service import GovernedImprovementService


def service(tmp_path):
    return GovernedImprovementService(tmp_path / "improvement", freshness_days=30)


def add_successes(value, *, count=5, task_class="invoice.match", route="local.model", procedure="procedure.v1", start=None):
    start = start or datetime.now(UTC)
    for index in range(count):
        value.record_outcome(outcome_id=f"outcome.{task_class}.{index}", task_class=task_class,
                             route_id=route, procedure_id=procedure, verified=True,
                             authority_ref=f"receipt.{index}", score=.9,
                             observed_at=(start + timedelta(minutes=index)).isoformat())


def test_corrections_and_outcomes_are_separate_from_conversation(tmp_path):
    value = service(tmp_path)
    correction = value.record_correction(correction_id="correction.1", task_class="invoice.match",
                                         target_ref="invoice.1", corrected_value={"supplier": "Acme"},
                                         actor_id="person.owner", conversation_ref="private words")
    outcome = value.record_outcome(outcome_id="outcome.1", task_class="invoice.match", route_id="local",
                                   procedure_id="p1", verified=True, authority_ref="receipt.1", score=.8)
    assert correction["conversation_content_stored"] is False
    assert outcome["conversation_content_stored"] is False
    assert value.corrections_path != value.outcomes_path


def test_route_preference_requires_three_fresh_verified_outcomes(tmp_path):
    value = service(tmp_path)
    add_successes(value, count=2)
    assert value.preference(task_class="invoice.match")["status"] == "insufficient_fresh_evidence"
    value.record_outcome(outcome_id="outcome.invoice.match.2", task_class="invoice.match", route_id="local.model",
                         procedure_id="procedure.v1", verified=True, authority_ref="receipt.2", score=.95)
    assert value.preference(task_class="invoice.match")["preferred"]["route_id"] == "local.model"


def test_stale_success_loses_preference_authority(tmp_path):
    value = service(tmp_path)
    old = datetime(2025, 1, 1, tzinfo=UTC)
    add_successes(value, count=3, start=old)
    value.refresh_preference(task_class="invoice.match", as_of=old.isoformat())
    assert value.preference(task_class="invoice.match", as_of=(old + timedelta(days=31)).isoformat())["status"] == "stale_revalidation_required"


def test_automation_needs_repetition_then_exact_owner_approval(tmp_path):
    value = service(tmp_path)
    with pytest.raises(ValueError, match="repeated_verified_evidence_required"):
        value.propose_automation(task_class="invoice.match", proposed_by="aion")
    add_successes(value)
    proposal = value.propose_automation(task_class="invoice.match", proposed_by="aion")
    assert proposal["execution_authority"] is False
    with pytest.raises(ValueError, match="integrity"):
        value.approve_automation(proposal_id=proposal["proposal_id"], proposal_hash="bad", owner_id="owner")
    approved = value.approve_automation(proposal_id=proposal["proposal_id"], proposal_hash=proposal["proposal_hash"], owner_id="owner")
    assert approved["status"] == "approved_but_unactivated"
    assert approved["execution_authority"] is False


def test_dataset_requires_licence_consent_purpose_and_redaction(tmp_path):
    value = service(tmp_path)
    with pytest.raises(ValueError, match="licence"):
        value.curate_dataset(dataset_id="d1", owner_id="owner", licence="unknown", consent_ref="c1", source_refs=["s1"], records=[], permitted_purposes=["evaluation"])
    with pytest.raises(ValueError, match="sensitive_field"):
        value.curate_dataset(dataset_id="d1", owner_id="owner", licence="customer_owned", consent_ref="c1", source_refs=["s1"], records=[{"api_token": "no"}], permitted_purposes=["evaluation"])
    dataset = value.curate_dataset(dataset_id="d1", owner_id="owner", licence="customer_owned", consent_ref="c1", source_refs=["s1"], records=[{"label": "paid", "amount_band": "small"}], permitted_purposes=["evaluation", "fine_tune"])
    assert dataset["raw_content_stored_in_registry"] is False
    assert dataset["record_count"] == 1


def test_model_release_is_reviewed_reversible_and_evidence_gated(tmp_path):
    value = service(tmp_path)
    value.curate_dataset(dataset_id="d1", owner_id="owner", licence="customer_owned", consent_ref="c1", source_refs=["s1"], records=[{"label": "ok"}], permitted_purposes=["fine_tune"])
    release = value.stage_model_release(release_id="model.v2", base_model_ref="model.v1", dataset_ids=["d1"], method="fine_tune", reviewed_by="reviewer", rollback_to="model.v1")
    assert release["active"] is False
    with pytest.raises(ValueError, match="retention_and_unfamiliar_transfer"):
        value.promote_release(release_id="model.v2", owner_id="owner")
    retained_at = (datetime.fromisoformat(release["created_at"]) + timedelta(days=2)).isoformat()
    value.record_release_evaluation(release_id="model.v2", evaluation_id="eval.retention", cohort="retention", passed=True, authority_ref="sealed.retention", observed_at=retained_at)
    value.record_release_evaluation(release_id="model.v2", evaluation_id="eval.transfer", cohort="unfamiliar_transfer", passed=True, authority_ref="sealed.transfer", source_disjoint=True)
    promoted = value.promote_release(release_id="model.v2", owner_id="owner")
    assert promoted["active"] is True
    assert promoted["rollback_to"] == "model.v1"


def test_revoked_dataset_cannot_enter_new_release(tmp_path):
    value = service(tmp_path)
    value.curate_dataset(dataset_id="d1", owner_id="owner", licence="customer_owned", consent_ref="c1", source_refs=["s1"], records=[{"label": "ok"}], permitted_purposes=["fine_tune"])
    value.revoke_dataset(dataset_id="d1", owner_id="owner")
    with pytest.raises(ValueError, match="eligible_dataset_required"):
        value.stage_model_release(release_id="model.v2", base_model_ref="model.v1", dataset_ids=["d1"], method="fine_tune", reviewed_by="reviewer", rollback_to="model.v1")


def test_customer_can_see_why_and_reverse_automation_change(tmp_path):
    value = service(tmp_path)
    add_successes(value)
    proposal = value.propose_automation(task_class="invoice.match", proposed_by="aion")
    value.approve_automation(proposal_id=proposal["proposal_id"], proposal_hash=proposal["proposal_hash"], owner_id="owner")
    changes = value.customer_changes()
    change = next(item for item in changes["changes"] if item["kind"] == "automation_approved")
    assert change["why"] == "automation approved"
    reversed_change = value.reverse_change(change_id=change["change_id"], owner_id="owner")
    assert reversed_change["reversed_by"] == "owner"
    automation = next(item for item in value._records(value.automations_path) if item["proposal_id"] == proposal["proposal_id"])
    assert automation["status"] == "disabled"
