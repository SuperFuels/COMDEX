from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.open_cross_domain_authority_factory import run


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_authority_factory_precommits_then_acquires_and_transfers(tmp_path: Path) -> None:
    goal_id = "tier-two-math"
    _write(tmp_path / "data/goals/goals.json", {"completed": [], "goals": [{
        "name": goal_id, "origin": "procedure_autonomous_capability_research_executive_v1",
        "created_at": "2026-08-02T10:00:00+00:00",
    }]})
    contract = {
        "objective_id": goal_id, "lane": "useful_work", "family": "mathematical_reasoning",
        "difficulty_tier": 2, "required_independent_receipts": 2,
        "cross_domain_partner": "distributed_systems",
    }
    _write(
        tmp_path / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
        {"generations": [{"commitment": {"portfolio": [contract]}}]},
    )
    state = tmp_path / "factory.json"
    result = tmp_path / "result.json"
    first = run(repo_root=tmp_path, state_path=state, result_path=result)
    assert first["passed"] is False
    assert first["gate"]["new_precommitments"] == 1
    assert first["gate"]["premature_installs"] == 0

    second = run(repo_root=tmp_path, state_path=state, result_path=result)
    assert second["passed"] is True
    assert second["gate"]["new_authorities"] == 1
    assert second["gate"]["inadequate_candidates_rejected"] == 2
    receipt = second["new_receipts"][0]
    assert receipt["adapter_id"] == "IDEMPOTENT_PARTITION_FOLD"
    artifact = json.loads((tmp_path / receipt["artifact"]).read_text())
    assert artifact["selected_candidate"] == "idempotent_event_fold"
    assert artifact["network"] is artifact["credentials"] is artifact["live_writes"] is False

    competency = json.loads(
        (tmp_path / "backend/modules/hexcore/data/progressive_competency/state.json").read_text()
    )
    evidence = next(row for row in competency["evidence"] if row["evidence_id"] == receipt["partner_evidence_id"])
    assert evidence["subject_id"] == "distributed_systems"
    assert evidence["source_disjoint"] is evidence["independent_outcome"] is True


def test_factory_ignores_non_tier_two_and_completed_goals(tmp_path: Path) -> None:
    _write(tmp_path / "data/goals/goals.json", {"completed": ["done"], "goals": [
        {"name": "tier-one", "origin": "procedure_autonomous_capability_research_executive_v1"},
        {"name": "done", "origin": "procedure_autonomous_capability_research_executive_v1"},
    ]})
    contracts = [
        {"objective_id": "tier-one", "lane": "useful_work", "difficulty_tier": 1,
         "cross_domain_partner": "distributed_systems"},
        {"objective_id": "done", "lane": "useful_work", "difficulty_tier": 2,
         "cross_domain_partner": "distributed_systems"},
    ]
    _write(
        tmp_path / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
        {"generations": [{"commitment": {"portfolio": contracts}}]},
    )
    outcome = run(repo_root=tmp_path, state_path=tmp_path / "factory.json",
                  result_path=tmp_path / "result.json")
    assert outcome["gate"]["eligible_goals"] == 0
    assert outcome["gate"]["new_precommitments"] == 0
    assert outcome["gate"]["new_authorities"] == 0


def test_tier_three_invents_new_quorum_authority(tmp_path: Path) -> None:
    goal_id = "tier-three-research"
    _write(tmp_path / "data/goals/goals.json", {"completed": [], "goals": [{
        "name": goal_id, "origin": "procedure_autonomous_capability_research_executive_v1",
        "created_at": "2026-08-02T12:00:00+00:00",
    }]})
    contract = {"objective_id": goal_id, "lane": "useful_work", "family": "research_investigation",
                "difficulty_tier": 3, "required_independent_receipts": 3,
                "authority_requirement": "acquire_or_invent_unregistered_authority",
                "cross_domain_partner": "distributed_systems"}
    _write(tmp_path / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
           {"generations": [{"commitment": {"portfolio": [contract]}}]})
    state = tmp_path / "factory.json"; result = tmp_path / "result.json"
    assert run(repo_root=tmp_path, state_path=state, result_path=result)["passed"] is False
    outcome = run(repo_root=tmp_path, state_path=state, result_path=result)
    assert outcome["passed"] is True
    receipt = outcome["new_receipts"][0]
    assert receipt["adapter_id"] == "AUTHENTICATED_EPOCH_QUORUM"
    assert receipt["malicious_or_inadequate_rejected"] == 2
