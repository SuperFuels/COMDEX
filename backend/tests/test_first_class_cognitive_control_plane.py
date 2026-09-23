from __future__ import annotations

import json

from backend.modules.hexcore.first_class_cognitive_control_plane import (
    FirstClassCognitiveControlPlane,
)


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _control(tmp_path):
    competency = tmp_path / "competency.json"
    registry = tmp_path / "registry.json"
    associations = tmp_path / "associations.json"
    experience = tmp_path / "experience"
    skills = tmp_path / "executive_skills.json"
    _write(
        competency,
        {
            "subjects": {
                "web_development": {
                    "name": "Web development HTML CSS",
                    "group": "computing",
                    "overall_level": "advanced",
                    "knowledge_level": "advanced",
                    "practical_level": "intermediate",
                    "per_subskill": {"html": {}, "css": {}, "tailwind": {}},
                },
                "software_engineering": {
                    "name": "Software engineering",
                    "group": "computing",
                    "overall_level": "intermediate",
                    "knowledge_level": "advanced",
                    "practical_level": "intermediate",
                    "per_subskill": {"testing": {}, "architecture": {}},
                },
            }
        },
    )
    _write(
        registry,
        {"adapters": {"web_development": {"status": "verified_available"}}},
    )
    _write(
        associations,
        {
            "relationships": {
                "edge": {
                    "source": "web_development",
                    "target": "software_engineering",
                    "relation": "SHARES_CONCEPT",
                    "strength": 0.9,
                }
            }
        },
    )
    _write(
        experience / "capsules" / "website.json",
        {
            "capsule_id": "website-v1",
            "title": "Build an HTML website with separate CSS",
            "knowledge_container_refs": ["subject__web_development"],
            "experience_claim": "A separated stylesheet improved reuse.",
            "wisdom_rule": "Choose inline or separate CSS deliberately; do not improvise inconsistently.",
            "knowledge_to_action_gap": "Responsive layout needed an explicit viewport test.",
            "repair": "Add browser-width checks.",
            "passed": True,
        },
    )
    _write(skills, {"skill_outcomes": {"web_delivery": {"attempts": 3, "verified": 2}}})
    return FirstClassCognitiveControlPlane(
        repo_root=tmp_path,
        canonical_state_path=tmp_path / "canonical.json",
        state_path=tmp_path / "control.json",
        authority_provider=lambda _goal: {"allow_learn": True},
        association_state_path=associations,
        competency_status_path=competency,
        executor_registry_path=registry,
        experience_root=experience,
        executive_skills_path=skills,
    )


def test_repetition_never_promotes_unverified_chatter(tmp_path):
    control = _control(tmp_path)
    for index in range(1000):
        result = control.observe_encounter(
            subject="the moon",
            predicate="is made of",
            object_value="cheese",
            source_id=f"user-{index}",
            source_type="conversation",
        )

    assert result["observation_count"] == 1000
    assert result["independent_source_count"] == 1000
    assert result["status"] == "encountered_unverified"
    assert result["repetition_promoted"] is False
    assert control.status()["canonical_active_claims"] == 0


def test_verified_promotion_uses_canonical_store_and_evidence(tmp_path):
    control = _control(tmp_path)
    encounter = control.observe_encounter(
        subject="HTML",
        predicate="uses",
        object_value="structured markup",
        source_id="candidate-source",
        source_type="research",
    )
    rejected = control.promote_encounter(
        encounter_id=encounter["encounter_id"],
        verifier="",
        verification_method="repetition",
        evidence_refs=[],
    )
    promoted = control.promote_encounter(
        encounter_id=encounter["encounter_id"],
        verifier="standards-checker",
        verification_method="human_authority",
        evidence_refs=["evidence://html-standard"],
    )

    assert rejected == {"promoted": False, "reason": "VERIFIED_PROVENANCE_REQUIRED"}
    assert promoted["promoted"] is True
    assert control.status()["canonical_active_claims"] == 1
    assert control.status()["verified_promotions"] == 1


def test_task_preparation_recalls_experience_skills_and_associations(tmp_path):
    control = _control(tmp_path)
    context = control.prepare_task("Build me an HTML website and style it with CSS")

    assert context["status"] == "prepared"
    assert context["experiential_memory"][0]["capsule_id"] == "website-v1"
    assert any(row["skill_id"] == "web_development" for row in context["required_skills"])
    assert any(row.get("target") == "software_engineering" for row in context["relevant_associations"])
    assert "software_engineering" in context["missing_capabilities"]
    assert context["known_failures_and_lessons"][0]["repair"] == "Add browser-width checks."
    assert context["task_policy"]["fresh_invention_status_until_verified"] == "proposal"


def test_conflicting_encounter_is_labelled_and_never_overrides_truth(tmp_path):
    control = _control(tmp_path)
    first = control.observe_encounter(
        subject="deployment",
        predicate="requires",
        object_value="tests",
        source_id="verified-candidate",
        source_type="research",
    )
    assert control.promote_encounter(
        encounter_id=first["encounter_id"],
        verifier="ci",
        verification_method="executable",
        evidence_refs=["receipt://ci-pass"],
    )["promoted"]

    conflict = control.observe_encounter(
        subject="deployment",
        predicate="requires",
        object_value="no tests",
        source_id="crowd-rumour",
        source_type="conversation",
    )
    context = control.prepare_task("What does deployment require?")

    assert conflict["canonical_conflict"] is True
    assert context["canonical_truth"][0]["claim"]["object"] == "tests"
    assert context["encountered_unverified"][0]["canonical_conflict"] is True
    assert context["encountered_unverified"][0]["status"] == "unverified_research_lead_only"


def test_task_outcome_requires_provenance_when_marked_verified(tmp_path):
    control = _control(tmp_path)
    context = control.prepare_task("Build an HTML website")
    rejected = control.record_task_outcome(
        trace_id=context["trace_id"],
        used_memory_ids=["website-v1"],
        used_skill_ids=["web_development"],
        outcome="passed",
        verified=True,
    )
    accepted = control.record_task_outcome(
        trace_id=context["trace_id"],
        used_memory_ids=["website-v1"],
        used_skill_ids=["web_development"],
        outcome="passed",
        verified=True,
        verifier="browser-test",
        evidence_refs=["receipt://browser-test"],
    )

    assert rejected["recorded"] is False
    assert accepted["recorded"] is True
    assert accepted["outcome"]["canonical_learning_authorized"] is False
