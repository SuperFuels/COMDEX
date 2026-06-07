from __future__ import annotations

import pytest

from backend.services.aion_mission_mode.template_learning_proposal import (
    TemplateApprovalRequired,
    approve_template_proposal,
    assert_template_save_allowed,
    canonical_hash,
    create_template_improvement_proposal,
    generate_template_diff,
    save_approved_template,
)


def current_template():
    return {
        "template_id": "lead_campaign_v1",
        "steps": ["draft_offer", "draft_ad"],
        "approval_required": True,
    }


def proposed_template():
    return {
        "template_id": "lead_campaign_v2",
        "steps": ["draft_offer", "draft_ad", "draft_landing_page"],
        "approval_required": True,
        "blocked_actions_panel": True,
    }


def make_proposal():
    return create_template_improvement_proposal(
        mission_id="mission_20o",
        mission_run_id="run_001",
        business_id="home_fixed",
        source_template_id="lead_campaign_v1",
        proposed_template_id="lead_campaign_v2",
        source_mission_receipt_hash="sha256:receipt",
        ets_preview_hash="sha256:ets_preview",
        current_template=current_template(),
        proposed_template=proposed_template(),
        reason="Mission produced a reusable safer lead generation pattern.",
    )


def test_phase20o_diff_detects_added_and_changed_fields():
    diff = generate_template_diff(current_template(), proposed_template())

    assert "blocked_actions_panel" in diff["added_fields"]
    assert "template_id" in diff["changed_fields"]
    assert diff["current_template_hash"].startswith("sha256:")
    assert diff["proposed_template_hash"].startswith("sha256:")
    assert diff["proposed_template_diff_hash"].startswith("sha256:")


def test_phase20o_creates_waiting_approval_proposal():
    proposal = make_proposal()

    assert proposal["proposal_type"] == "template_improvement_proposal"
    assert proposal["proposal_state"] == "waiting_human_approval"
    assert proposal["requires_human_approval"] is True
    assert proposal["approved"] is False
    assert proposal["live_template_mutation_allowed"] is False
    assert proposal["template_improvement_proposal_hash"].startswith("sha256:")


def test_phase20o_links_source_mission_and_ets_preview():
    proposal = make_proposal()

    assert proposal["source_mission_receipt_hash"] == "sha256:receipt"
    assert proposal["ets_preview_hash"] == "sha256:ets_preview"


def test_phase20o_unapproved_template_save_is_blocked():
    proposal = make_proposal()
    assertion = assert_template_save_allowed(proposal, proposed_template())

    assert assertion["template_save_allowed"] is False
    assert "human_approval_required" in assertion["reasons"]


def test_phase20o_approval_produces_approval_hash():
    proposal = make_proposal()
    approved = approve_template_proposal(
        proposal,
        approver_id="founder",
        approval_note="Approve as reusable Home Fixed campaign template.",
    )

    assert approved["approved"] is True
    assert approved["proposal_state"] == "approved_for_template_save"
    assert approved["approval_hash"].startswith("sha256:")
    assert approved["approved_proposal_hash"].startswith("sha256:")


def test_phase20o_approved_template_save_allowed():
    approved = approve_template_proposal(
        make_proposal(),
        approver_id="founder",
        approval_note="Approved.",
    )
    assertion = assert_template_save_allowed(approved, proposed_template())

    assert assertion["template_save_allowed"] is True
    assert assertion["reasons"] == ["template_save_approved_and_hash_bound"]


def test_phase20o_template_hash_mismatch_blocks_save():
    approved = approve_template_proposal(
        make_proposal(),
        approver_id="founder",
        approval_note="Approved.",
    )
    mutated = proposed_template()
    mutated["approval_required"] = False

    assertion = assert_template_save_allowed(approved, mutated)

    assert assertion["template_save_allowed"] is False
    assert "proposed_template_hash_mismatch" in assertion["reasons"]


def test_phase20o_save_record_is_business_container_bound(tmp_path):
    approved = approve_template_proposal(
        make_proposal(),
        approver_id="founder",
        approval_note="Approved.",
    )
    record = save_approved_template(
        business_container_root=str(tmp_path),
        proposal=approved,
        proposed_template=proposed_template(),
    )

    assert record["relative_template_path"] == "templates/approved/lead_campaign_v2.json"
    assert str(tmp_path.resolve()) in record["contained_template_path"]
    assert record["template_save_record_hash"].startswith("sha256:")


def test_phase20o_save_without_approval_raises(tmp_path):
    with pytest.raises(TemplateApprovalRequired):
        save_approved_template(
            business_container_root=str(tmp_path),
            proposal=make_proposal(),
            proposed_template=proposed_template(),
        )


def test_phase20o_hash_is_deterministic():
    left = canonical_hash({"b": 2, "a": 1})
    right = canonical_hash({"a": 1, "b": 2})

    assert left == right


def test_phase20o_proposal_does_not_mutate_inputs():
    current = current_template()
    proposed = proposed_template()
    current_before = dict(current)
    proposed_before = dict(proposed)

    make = create_template_improvement_proposal(
        mission_id="m",
        mission_run_id="r",
        business_id="b",
        source_template_id="s",
        proposed_template_id="p",
        source_mission_receipt_hash="sha256:x",
        ets_preview_hash="sha256:y",
        current_template=current,
        proposed_template=proposed,
        reason="test",
    )

    assert make["template_improvement_proposal_hash"].startswith("sha256:")
    assert current == current_before
    assert proposed == proposed_before


def test_phase20o_templates_cannot_mutate_silently():
    proposal = make_proposal()
    approved = approve_template_proposal(
        proposal,
        approver_id="founder",
        approval_note="Approved.",
    )
    tampered = proposed_template()
    tampered["new_unapproved_field"] = "silent mutation"

    assertion = assert_template_save_allowed(approved, tampered)

    assert assertion["template_save_allowed"] is False
    assert "proposed_template_hash_mismatch" in assertion["reasons"]
