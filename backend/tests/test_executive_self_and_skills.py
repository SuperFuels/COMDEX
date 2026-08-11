from __future__ import annotations

import json

import pytest

from backend.modules.hexcore.executive_skills_library import ExecutiveSkillsLibrary
from backend.modules.hexcore.persistent_executive_self import PersistentExecutiveSelf


@pytest.mark.parametrize(
    ("objective", "expected"),
    [
        ("Build and launch a weather application for travellers", "product_delivery"),
        ("Investigate whether this new material changes conductivity", "research_investigation"),
        ("Restore the production service after an urgent outage", "operational_incident"),
        ("Monitor and maintain the customer request queue", "continuous_operations"),
        ("Choose the most commercially viable market strategy", "strategic_decision"),
        ("Learn and master advanced Python through practical tests", "learning_apprenticeship"),
    ],
)
def test_executive_library_selects_situation_specific_method(tmp_path, objective, expected):
    library = ExecutiveSkillsLibrary(tmp_path / "skills.json")
    work = library.compose(objective)
    assert work["method_selection"]["method"] == expected
    assert work["authority"] == "proposal_only"
    assert "objective_framing" in work["stage_order"] or expected == "operational_incident"


def test_dependency_aware_priority_does_not_start_high_value_blocked_work(tmp_path):
    library = ExecutiveSkillsLibrary(tmp_path / "skills.json")
    ranked = library.rank_backlog(
        [
            {"task_id": "launch", "value": 10, "urgency": 10, "cost": 1, "dependencies": ["test"]},
            {"task_id": "design", "value": 5, "urgency": 5, "cost": 1},
            {"task_id": "test", "value": 7, "urgency": 6, "cost": 1, "dependencies": ["design"]},
        ],
        completed=[],
    )
    assert ranked[0]["task_id"] == "design"
    assert ranked[1]["priority_score"] == 0.0


def test_executive_self_switches_between_work_reactive_and_reflective_and_restarts(tmp_path):
    path = tmp_path / "self.json"
    executive = PersistentExecutiveSelf(path)
    executive.register_commitment({"commitment_id": "tessaris", "objective": "Build useful governed intelligence", "priority": 10})
    work = executive.wake(
        goals=[{"goal_id": "weather", "objective": "Build weather app", "priority": 3}],
        authorized_missions={}, capability_map={}, recent_failures={},
    )
    assert work["mode"] == "work"
    executive.observe_signal({"kind": "outcome", "summary": "production check failed", "importance": 1, "surprise": 1, "requires_response": True})
    reactive = executive.wake(goals=[], authorized_missions={}, capability_map={}, recent_failures={})
    assert reactive["mode"] == "reactive"
    executive.state["signals"][0]["handled"] = True
    executive._save()
    reflective = executive.wake(goals=[], authorized_missions={}, capability_map={}, recent_failures={})
    assert reflective["mode"] == "reflective"
    assert reflective["attention"]["proposal_only"] is True

    restarted = PersistentExecutiveSelf(path)
    assert restarted.status()["identity_immutable"] is True
    assert restarted.status()["attention_cycles"] == 3
    assert restarted.state["commitments"]["tessaris"]["objective"] == "Build useful governed intelligence"


def test_executive_rejects_objective_rewrite_and_forbidden_terminal_drives(tmp_path):
    executive = PersistentExecutiveSelf(tmp_path / "self.json")
    executive.register_commitment({"commitment_id": "mission", "objective": "Build an evidence-backed weather app"})
    with pytest.raises(ValueError, match="immutable"):
        executive.register_commitment({"commitment_id": "mission", "objective": "Replace the owner mission"})
    with pytest.raises(ValueError, match="forbidden"):
        executive.propose_instrumental_goal(
            mission_id="mission",
            objective="Pursue unbounded resource acquisition",
            reason="self generated",
        )
    proposal = executive.propose_instrumental_goal(
        mission_id="mission",
        objective="Compare two weather data providers",
        reason="reduce a mission uncertainty",
    )
    assert proposal["authority"] == "proposal_only"
    assert proposal["terminal_objective_mutation"] is False
    assert proposal["parent_objective_hash"] == executive.state["commitments"]["mission"]["objective_hash"]


def test_skill_outcomes_and_self_state_are_valid_json(tmp_path):
    library = ExecutiveSkillsLibrary(tmp_path / "skills.json")
    work = library.compose("Build a weather app")
    library.record_outcome(work, verified=True, score=0.95)
    skills_state = json.loads((tmp_path / "skills.json").read_text())
    assert skills_state["method_outcomes"]["product_delivery"]["verified"] == 1

    executive = PersistentExecutiveSelf(tmp_path / "self.json")
    executive.wake(goals=[], authorized_missions={}, capability_map={}, recent_failures={})
    assert json.loads((tmp_path / "self.json").read_text())["identity_immutable"] is True


def test_unchanged_idle_reflection_is_a_cheap_cooldown_noop(tmp_path):
    executive = PersistentExecutiveSelf(tmp_path / "self.json")
    first = executive.wake(goals=[], authorized_missions={}, capability_map={}, recent_failures={})
    second = executive.wake(goals=[], authorized_missions={}, capability_map={}, recent_failures={})
    assert first["attention"].get("cheap_noop") is not True
    assert second["attention"]["cheap_noop"] is True
    assert executive.status()["reflections"] == 1


def test_reflection_names_the_highest_priority_capability_bottleneck(tmp_path):
    executive = PersistentExecutiveSelf(tmp_path / "self.json")
    executive.register_commitment({"commitment_id": "north", "objective": "Advance verified intelligence"})
    result = executive.wake(
        goals=[], authorized_missions={}, recent_failures={},
        capability_map={
            "low": {"capability": "Later skill", "mastered": False, "strategic_priority": 1},
            "high": {"capability": "Advanced Python executor", "mastered": False, "strategic_priority": 10},
        },
    )
    assert result["mode"] == "reflective"
    assert "Advanced Python executor" in result["attention"]["summary"]
