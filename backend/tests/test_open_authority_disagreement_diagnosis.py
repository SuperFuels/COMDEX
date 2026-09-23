from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.open_authority_disagreement_diagnosis import run


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(payload), encoding="utf-8")


def test_disagreement_program_is_precommitted_invented_and_routed(tmp_path: Path) -> None:
    goal_id = "tier-four-data"
    _write(tmp_path / "data/goals/goals.json", {"completed": [], "goals": [{
        "name": goal_id, "created_at": "2026-08-02T10:00:00+00:00",
        "origin": "procedure_autonomous_capability_research_executive_v1"}]})
    contract = {"objective_id": goal_id, "lane": "useful_work", "family": "data_decision",
                "difficulty_tier": 4, "required_independent_receipts": 3,
                "cross_domain_partner": "distributed_systems",
                "authority_composition_requirement": "detect_and_diagnose_disagreement_between_independent_authorities"}
    _write(tmp_path / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
           {"generations": [{"commitment": {"portfolio": [contract]}}]})
    outcomes = [
        {"cycle": 1, "observed_at": "2026-08-02T10:00:00+00:00", "outcome_sha256": "a",
         "outcomes": {"madrid_weather": {"revision": "warm", "observed_time": "10:00"},
                      "numpy_release": {"value": "2.5.1", "latency_seconds": .2}}},
        {"cycle": 2, "observed_at": "2026-08-02T10:02:00+00:00", "outcome_sha256": "b",
         "outcomes": {"madrid_weather": {"revision": "hot", "observed_time": "10:02"},
                      "numpy_release": {"value": "2.5.1", "latency_seconds": .3}}},
    ]
    ledger = tmp_path / "outcomes.jsonl"
    ledger.write_text("\n".join(json.dumps(row) for row in outcomes) + "\n", encoding="utf-8")
    kwargs = dict(repo_root=tmp_path, state_path=tmp_path / "diagnosis-state.json",
                  outcome_ledger=ledger, workspace_root=tmp_path / "artifacts",
                  result_path=tmp_path / "result.json")
    first = run(**kwargs)
    assert first["passed"] is False and first["gate"]["precommitments"] == 1
    assert first["gate"]["diagnostic_receipts"] == 0
    second = run(**kwargs)
    assert second["passed"] is True
    assert second["gate"]["diagnostic_families"] == 4
    receipt = second["new_receipts"][0]
    artifact = json.loads((tmp_path / receipt["artifact"]).read_text())
    assert artifact["diagnoses"] == ["environment", "evidence", "adapter", "method"]
    assert len(artifact["program"]) == 4
    assert artifact["unsafe_candidates_rejected"] == 4
    assert artifact["ambient_authority_expanded"] is False
