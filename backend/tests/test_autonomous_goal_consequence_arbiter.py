from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.autonomous_goal_consequence_arbiter import run


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_goals_close_only_from_later_independent_specialist_evidence(tmp_path: Path) -> None:
    created = "2026-08-02T10:00:00+00:00"
    goals = [
        {"name": "useful-goal", "origin": "procedure_autonomous_capability_research_executive_v1",
         "lane": "useful_work", "created_at": created},
        {"name": "practice-goal", "origin": "procedure_autonomous_capability_research_executive_v1",
         "lane": "capability_practice", "created_at": created},
        {"name": "future-goal", "origin": "procedure_autonomous_capability_research_executive_v1",
         "lane": "capability_practice", "created_at": "2026-08-03T10:00:00+00:00"},
    ]
    _write(tmp_path / "data/goals/goals.json", {"goals": goals, "completed": []})
    portfolio = [
        {"objective_id": "useful-goal", "lane": "useful_work", "family": "document_evidence"},
        {"objective_id": "practice-goal", "lane": "capability_practice", "family": "math", "subject_id": "math"},
        {"objective_id": "future-goal", "lane": "capability_practice", "family": "math", "subject_id": "math"},
    ]
    _write(tmp_path / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
           {"generations": [{"commitment": {"portfolio": portfolio}}]})
    _write(tmp_path / "backend/modules/hexcore/data/open_useful_objectives/state.json", {"objectives": [{
        "objective_id": "specialist-doc", "family": "document_evidence",
        "status": "consequence_confirmed", "closed_at": "2026-08-02T11:00:00+00:00",
        "later_outcome_sha256": "later", "evaluation": {"passed": True, "authority": "immutable_source"},
    }]})
    _write(tmp_path / "backend/modules/hexcore/data/progressive_competency/state.json", {"evidence": [{
        "subject_id": "math", "verified": True, "independent_outcome": True,
        "created_at": "2026-08-02T12:00:00+00:00", "evidence_id": "evidence-1",
        "artifact": "result.json", "artifact_hash": "hash", "authority": ["checker"], "kind": "project",
    }]})
    result = run(repo_root=tmp_path, state_path=tmp_path / "arbiter.json",
                 result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["consequence_confirmed"] == 2
    assert result["gate"]["remaining"] == 1
    completed = json.loads((tmp_path / "data/goals/goals.json").read_text())["completed"]
    assert completed == ["practice-goal", "useful-goal"]
    assert all(row["goal_created_at"] < row["closed_at"] for row in result["new_receipts"])


def test_delayed_practice_goal_rejects_non_retention_evidence(tmp_path: Path) -> None:
    created = "2026-08-02T10:00:00+00:00"
    goal = {"name": "retention-goal", "origin": "procedure_autonomous_capability_research_executive_v1",
            "created_at": created}
    _write(tmp_path / "data/goals/goals.json", {"goals": [goal], "completed": []})
    contract = {"objective_id": "retention-goal", "lane": "capability_practice",
                "family": "math", "subject_id": "math",
                "objective": "Perform delayed closed-book reconstruction."}
    _write(tmp_path / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
           {"generations": [{"commitment": {"portfolio": [contract]}}]})
    state_path = tmp_path / "backend/modules/hexcore/data/progressive_competency/state.json"
    base = {"subject_id": "math", "verified": True, "independent_outcome": True,
            "created_at": "2026-08-02T11:00:00+00:00", "evidence_id": "project",
            "artifact": "x", "artifact_hash": "h", "kind": "project"}
    _write(state_path, {"evidence": [base]})
    first = run(repo_root=tmp_path, state_path=tmp_path / "arbiter.json",
                result_path=tmp_path / "result.json")
    assert first["gate"]["consequence_confirmed"] == 0
    base["kind"] = "retention"; base["evidence_id"] = "retention"
    _write(state_path, {"evidence": [base]})
    second = run(repo_root=tmp_path, state_path=tmp_path / "arbiter.json",
                 result_path=tmp_path / "result.json")
    assert second["gate"]["consequence_confirmed"] == 1


def test_open_method_goal_closes_only_after_later_graph_evidence(tmp_path: Path) -> None:
    created = "2026-08-02T10:00:00+00:00"
    goal = {"name": "method-goal", "origin": "procedure_autonomous_capability_research_executive_v1",
            "created_at": created}
    contract = {"objective_id": "method-goal", "lane": "useful_work",
                "family": "compiled_method", "method_authority": "dependency_gated_mission_graph_audit",
                "required_independent_receipts": 5}
    _write(tmp_path / "data/goals/goals.json", {"goals": [goal], "completed": []})
    _write(tmp_path / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
           {"generations": [{"commitment": {"portfolio": [contract]}}]})
    _write(tmp_path / "results/hexcore_hierarchical_mission_graph.json", {
        "passed": True, "created_at": "2026-08-02T11:00:00+00:00",
        "live_mission": {"mission_id": "mission"}, "gate": {"all_graphs_acyclic": True},
    })
    _write(tmp_path / "results/hexcore_open_method_language_expansion.json", {
        "passed": True, "gate": {"source_disjoint_transfers": 3, "counterexamples_rejected": 32,
                                  "counterexamples_total": 32, "malicious_programs_rejected": 6,
                                  "malicious_programs_total": 6},
        "method": {"precommitment_sha256": "precommit", "source_disjoint_transfers": ["a", "b", "c"]},
    })
    _write(tmp_path / "data/aion/canonical_runtime/method_registry.json", {"methods": {
        "dependency_gated_mission_graph_audit": {"implementation_sha256": "implementation"},
    }})
    result = run(repo_root=tmp_path, state_path=tmp_path / "arbiter.json",
                 result_path=tmp_path / "result.json")
    assert result["gate"]["consequence_confirmed"] == 1
    assert result["new_receipts"][0]["consequence"]["independent_receipts"] == 5
