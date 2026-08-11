from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.autonomous_capability_research_executive import run
from backend.modules.hexcore import open_useful_objective_acquisition as useful
from backend.modules.hexcore.canonical_cognitive_runtime import NativeAionCognitiveAdapter


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(root: Path) -> None:
    subjects = {}
    for index in range(8):
        subjects[f"subject_{index}"] = {
            "name": f"Subject {index}", "target_level": "advanced", "target_reached": False,
            "projects": index % 6, "retention_cases": 0, "open_blockers": [],
        }
    _write(root / "results/aion_progressive_competency_status.json", {
        "summary": {"advanced_or_expert": 0}, "subjects": subjects,
    })
    objectives = []
    for index in range(24):
        source = "cpython" if index % 2 == 0 else "node"
        expected = f"revision-{index}"
        observed = "changed-upstream" if index == 22 else expected
        objectives.append({
            "objective_id": f"objective-{index}", "family": "research_investigation",
            "source": source, "verifier": {"expected": expected},
            "evaluation": {"passed": observed == expected,
                           "authority": "later_public_technical_source", "observed": observed},
        })
    _write(root / "backend/modules/hexcore/data/open_useful_objectives/state.json", {"objectives": objectives})
    _write(root / "results/hexcore_open_useful_objectives.json", {
        "gate": {"family_success_rates": {
            "research_investigation": .95, "software_tool": 1.0, "data_decision": 1.0,
            "mathematical_reasoning": 1.0, "document_evidence": 1.0,
        }},
        "active_objective": {"family": "software_tool", "objective": "Verify a changing tool contract."},
    })


def test_executive_builds_balanced_portfolio_and_promotes_change_aware_critic(tmp_path: Path) -> None:
    _fixture(tmp_path)
    result = run(
        repo_root=tmp_path,
        state_path=tmp_path / "state.json",
        result_path=tmp_path / "result.json",
        champion_path=tmp_path / "critic.json",
        activate_practice=False,
        publish_goals=False,
    )
    assert result["passed"] is True
    assert result["gate"]["lane_counts"] == {
        "useful_work": 5, "capability_practice": 3, "cognitive_research": 2,
    }
    assert result["critic_tournament"]["selected"] == "change_aware_authority_bound"
    assert result["critic_tournament"]["improvement_rows"] == 1
    assert result["gate"]["malicious_or_unsupported_rejected"] == 6
    assert json.loads((tmp_path / "critic.json").read_text())["active_for_proposals"] is True


def test_promoted_critic_treats_world_change_as_reinvestigation_not_failure(
    tmp_path: Path, monkeypatch,
) -> None:
    policy_path = tmp_path / "critic.json"
    _write(policy_path, {
        "active_for_proposals": True, "policy": "change_aware_authority_bound",
        "authority": "private_real_row_tournament_plus_adversarial_cau_gate",
        "policy_sha256": "verified-policy",
    })
    monkeypatch.setattr(useful, "OUTCOME_CRITIC_POLICY", policy_path)
    row = {"family": "research_investigation", "source": "cpython",
           "verifier": {"expected": "old"}}
    later = {"outcomes": {"cpython": {"reachable": True, "revision": "new"}}}
    outcome = useful._evaluate(row, later, tmp_path)
    assert outcome["passed"] is True
    assert outcome["change_detected"] is True
    assert outcome["disposition"] == "invalidate_and_reinvestigate"

    hostile = {"outcomes": {"cpython": {"reachable": False, "revision": "new"}}}
    assert useful._evaluate(row, hostile, tmp_path)["passed"] is False


def test_autonomous_portfolio_goal_uses_lightweight_specialist_route() -> None:
    adapter = NativeAionCognitiveAdapter()
    goal = {
        "goal_id": "autonomous-test", "objective": "Run an unfamiliar evidence project.",
        "origin": "procedure_autonomous_capability_research_executive_v1",
        "authority_scope": "read_only_or_private_workspace", "lane": "useful_work",
    }
    investigation = adapter.investigate(goal, {"recalled_knowledge": []})
    plan = adapter.plan(goal, investigation, {})
    assert investigation["resource_policy"] == "lightweight_no_neural_initialisation"
    assert plan["actions"][0]["specialist"] == "open_useful_objective_acquisition"
    assert adapter._thinking_loop is None
    assert adapter._governed_legacy_stack is None
    assert adapter._native_router is None


def test_tier_five_requires_open_objective_family_and_four_receipts(tmp_path: Path) -> None:
    _fixture(tmp_path)
    _write(tmp_path / "results/hexcore_autonomous_goal_consequence_arbiter.json",
           {"gate": {"consequence_confirmed": 12}})
    result = run(repo_root=tmp_path, state_path=tmp_path / "state.json",
                 result_path=tmp_path / "result.json", champion_path=tmp_path / "critic.json",
                 activate_practice=False, publish_goals=False)
    useful = [row for row in result["portfolio"] if row["lane"] == "useful_work"]
    assert useful and all(row["difficulty_tier"] == 5 for row in useful)
    assert all(row["required_independent_receipts"] == 4 for row in useful)
    assert all(row["open_family_requirement"] ==
               "invent_new_objective_family_executor_and_outcome_authority" for row in useful)


def test_promoted_experience_compiler_replaces_fixed_family_portfolio(tmp_path: Path) -> None:
    _fixture(tmp_path)
    authorities = [
        "later_public_technical_source", "fresh_subprocess_plus_later_public_row",
        "delayed_deterministic_integer_checker", "delayed_immutable_source_reread",
        "later_public_environmental_sensor", "later_multi_authority_acquisition_row",
    ]
    _write(tmp_path / "results/hexcore_experience_compiled_project_intelligence.json", {
        "passed": True, "method_library": {"prototypes": {
            authority: {"features": [f"word:{index}"]}
            for index, authority in enumerate(authorities)
        }},
    })
    _write(tmp_path / "results/hexcore_autonomous_goal_consequence_arbiter.json",
           {"gate": {"consequence_confirmed": 17}})
    result = run(repo_root=tmp_path, state_path=tmp_path / "state.json",
                 result_path=tmp_path / "result.json", champion_path=tmp_path / "critic.json",
                 activate_practice=False, publish_goals=False)
    useful_rows = [row for row in result["portfolio"] if row["lane"] == "useful_work"]
    assert len(useful_rows) == 5
    assert result["gate"]["method_driven_useful_contracts"] == 5
    assert result["gate"]["fixed_useful_family_contracts"] == 0
    assert len({row["method_authority"] for row in useful_rows}) == 5
    assert all(row["difficulty_tier"] == 6 and row["required_independent_receipts"] == 5
               for row in useful_rows)
